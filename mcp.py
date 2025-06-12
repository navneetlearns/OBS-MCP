import logging
from typing import Dict, Any
from mcp.server.fastmcp import FastMCP, Context
from obswebsocket import obsws, requests
import json

# Configure logging to write to a file
logging.basicConfig(
    filename='your file path',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

logger.info("Starting obs_mcp_server.py")

class OBSConnection:
    def __init__(self, host="localhost", port=4455, password="password"):
        self.host = host
        self.port = port
        self.password = password
        self.ws = None
        logger.info(f"Initialized OBSConnection with host={host}, port={port}")

    def connect(self) -> bool:
        try:
            self.ws = obsws(self.host, self.port, self.password)
            self.ws.connect()
            logger.info("Successfully connected to OBS WebSocket")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to OBS WebSocket: {e}")
            return False

    def disconnect(self):
        if self.ws:
            self.ws.disconnect()
            logger.info("Disconnected from OBS WebSocket")

    def send_command(self, command_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
        try:
            if command_type == "switch_scene":
                self.ws.call(requests.SetCurrentProgramScene(sceneName=params.get("scene_name")))
                logger.info(f"Switched to scene '{params.get('scene_name')}'")
                return {"success": True, "message": f"Switched to scene '{params.get('scene_name')}'"}
            elif command_type == "start_streaming":
                self.ws.call(requests.StartStream())
                logger.info("Streaming started")
                return {"success": True, "message": "Streaming started"}
            elif command_type == "stop_streaming":
                self.ws.call(requests.StopStream())
                logger.info("Streaming stopped")
                return {"success": True, "message": "Streaming stopped"}
            elif command_type == "start_recording":
                self.ws.call(requests.StartRecord())
                logger.info("Recording started")
                return {"success": True, "message": "Recording started"}
            elif command_type == "stop_recording":
                self.ws.call(requests.StopRecord())
                logger.info("Recording stopped")
                return {"success": True, "message": "Recording stopped"}
            elif command_type == "toggle_source_visibility":
                self.ws.call(requests.SetSceneItemEnabled(
                    sceneName=params.get("scene_name"),
                    sceneItemId=self._get_scene_item_id(params.get("scene_name"), params.get("source_name")),
                    enabled=params.get("enabled", True)
                ))
                logger.info(f"Source '{params.get('source_name')}' set to {'visible' if params.get('enabled') else 'hidden'}")
                return {"success": True, "message": f"Source '{params.get('source_name')}' set to {'visible' if params.get('enabled') else 'hidden'}"}
            elif command_type == "add_display_capture":
                scene_name = params.get("scene_name")
                source_name = params.get("source_name", "DisplayCapture")
                self.ws.call(requests.CreateSource(
                    sourceName=source_name,
                    sourceKind="monitor_capture",
                    sceneName=scene_name,
                    sourceSettings={},
                    setVisible=True
                ))
                logger.info(f"Added display capture source '{source_name}' to scene '{scene_name}'")
                return {"success": True, "message": f"Added display capture source '{source_name}' to scene '{scene_name}'"}
            elif command_type == "set_source_position":
                self.ws.call(requests.SetSceneItemTransform(
                    sceneName=params.get("scene_name"),
                    sceneItemId=self._get_scene_item_id(params.get("scene_name"), params.get("source_name")),
                    sceneItemTransform={
                        "positionX": params.get("x", 0),
                        "positionY": params.get("y", 0),
                        "scaleX": params.get("scale_x", 1.0),
                        "scaleY": params.get("scale_y", 1.0)
                    }
                ))
                logger.info(f"Set position of source '{params.get('source_name')}' in scene '{params.get('scene_name')}' to x={params.get('x')}, y={params.get('y')}, scaleX={params.get('scale_x')}, scaleY={params.get('scale_y')}")
                return {"success": True, "message": f"Set position of source '{params.get('source_name')}' in scene '{params.get('scene_name')}'"}
            elif command_type == "get_scene_list":
                response = self.ws.call(requests.GetSceneList())
                scenes = [scene["sceneName"] for scene in response.getScenes()]
                logger.info(f"Retrieved scene list: {scenes}")
                return {"success": True, "message": "Scenes retrieved", "scenes": scenes}
            elif command_type == "get_version":
                response = self.ws.call(requests.GetVersion())
                version = response.getObsWebSocketVersion()
                logger.info(f"OBS WebSocket version: {version}")
                return {"success": True, "message": f"OBS WebSocket version: {version}"}
            else:
                logger.warning(f"Unknown command: {command_type}")
                return {"success": False, "message": f"Unknown command: {command_type}"}
        except Exception as e:
            logger.error(f"OBS command error: {e}")
            return {"success": False, "message": str(e)}

    def _get_scene_item_id(self, scene_name: str, source_name: str) -> int:
        response = self.ws.call(requests.GetSceneItemList(sceneName=scene_name))
        for item in response.getSceneItems():
            if item["sourceName"] == source_name:
                return item["sceneItemId"]
        logger.error(f"Source '{source_name}' not found in scene '{scene_name}'")
        raise ValueError(f"Source '{source_name}' not found in scene '{scene_name}'")

_obs_connection = None

def get_obs_connection():
    global _obs_connection
    if _obs_connection is None or not _obs_connection.connect():
        _obs_connection = OBSConnection()
        if not _obs_connection.connect():
            logger.error("Could not connect to OBS WebSocket after initialization")
            raise ConnectionError("Could not connect to OBS WebSocket.")
    return _obs_connection

mcp = FastMCP("OBSMCP", description="OBS Studio integration via MCP")
logger.info("FastMCP instance created with name 'OBSMCP'")

@mcp.tool()
def switch_scene(ctx: Context, scene_name: str) -> str:
    """Switches to the specified scene in OBS Studio."""
    try:
        obs = get_obs_connection()
        result = obs.send_command("switch_scene", {"scene_name": scene_name})
        logger.info(f"switch_scene result: {result}")
        return json.dumps({"status": "success" if result["success"] else "error", "message": result["message"]})
    except Exception as e:
        logger.error(f"Error switching scene: {e}")
        return json.dumps({"status": "error", "message": str(e)})

@mcp.tool()
def start_streaming(ctx: Context) -> str:
    """Starts streaming in OBS Studio."""
    try:
        obs = get_obs_connection()
        result = obs.send_command("start_streaming", {})
        logger.info(f"start_streaming result: {result}")
        return json.dumps({"status": "success" if result["success"] else "error", "message": result["message"]})
    except Exception as e:
        logger.error(f"Error starting streaming: {e}")
        return json.dumps({"status": "error", "message": str(e)})

@mcp.tool()
def stop_streaming(ctx: Context) -> str:
    """Stops streaming in OBS Studio."""
    try:
        obs = get_obs_connection()
        result = obs.send_command("stop_streaming", {})
        logger.info(f"stop_streaming result: {result}")
        return json.dumps({"status": "success" if result["success"] else "error", "message": result["message"]})
    except Exception as e:
        logger.error(f"Error stopping streaming: {e}")
        return json.dumps({"status": "error", "message": str(e)})

@mcp.tool()
def start_recording(ctx: Context) -> str:
    """Starts recording in OBS Studio."""
    try:
        obs = get_obs_connection()
        result = obs.send_command("start_recording", {})
        logger.info(f"start_recording result: {result}")
        return json.dumps({"status": "success" if result["success"] else "error", "message": result["message"]})
    except Exception as e:
        logger.error(f"Error starting recording: {e}")
        return json.dumps({"status": "error", "message": str(e)})

@mcp.tool()
def stop_recording(ctx: Context) -> str:
    """Stops recording in OBS Studio."""
    try:
        obs = get_obs_connection()
        result = obs.send_command("stop_recording", {})
        logger.info(f"stop_recording result: {result}")
        return json.dumps({"status": "success" if result["success"] else "error", "message": result["message"]})
    except Exception as e:
        logger.error(f"Error stopping recording: {e}")
        return json.dumps({"status": "error", "message": str(e)})

@mcp.tool()
def toggle_source_visibility(ctx: Context, scene_name: str, source_name: str, enabled: bool = True) -> str:
    """Toggles visibility of a source in a specific scene."""
    try:
        obs = get_obs_connection()
        result = obs.send_command("toggle_source_visibility", {
            "scene_name": scene_name,
            "source_name": source_name,
            "enabled": enabled
        })
        logger.info(f"toggle_source_visibility result: {result}")
        return json.dumps({"status": "success" if result["success"] else "error", "message": result["message"]})
    except Exception as e:
        logger.error(f"Error toggling source visibility: {e}")
        return json.dumps({"status": "error", "message": str(e)})

@mcp.tool()
def add_display_capture(ctx: Context, scene_name: str, source_name: str = "DisplayCapture") -> str:
    """Adds a display capture source to the specified scene to share the desktop screen."""
    try:
        obs = get_obs_connection()
        result = obs.send_command("add_display_capture", {
            "scene_name": scene_name,
            "source_name": source_name
        })
        logger.info(f"add_display_capture result: {result}")
        return json.dumps({"status": "success" if result["success"] else "error", "message": result["message"]})
    except Exception as e:
        logger.error(f"Error adding display capture: {e}")
        return json.dumps({"status": "error", "message": str(e)})

@mcp.tool()
def set_source_position(ctx: Context, scene_name: str, source_name: str, x: int = 0, y: int = 0, scale_x: float = 1.0, scale_y: float = 1.0) -> str:
    """Sets the position and scale of a source in a specific scene."""
    try:
        obs = get_obs_connection()
        result = obs.send_command("set_source_position", {
            "scene_name": scene_name,
            "source_name": source_name,
            "x": x,
            "y": y,
            "scale_x": scale_x,
            "scale_y": scale_y
        })
        logger.info(f"set_source_position result: {result}")
        return json.dumps({"status": "success" if result["success"] else "error", "message": result["message"]})
    except Exception as e:
        logger.error(f"Error setting source position: {e}")
        return json.dumps({"status": "error", "message": str(e)})

@mcp.tool()
def get_scene_list(ctx: Context) -> str:
    """Retrieves a list of all scenes in OBS Studio."""
    try:
        obs = get_obs_connection()
        result = obs.send_command("get_scene_list", {})
        logger.info(f"get_scene_list result: {result}")
        return json.dumps({"status": "success" if result["success"] else "error", "message": result["message"], "scenes": result.get("scenes", [])})
    except Exception as e:
        logger.error(f"Error getting scene list: {e}")
        return json.dumps({"status": "error", "message": str(e)})

@mcp.tool()
def test_obs_connection(ctx: Context) -> str:
    """Tests the connection to OBS WebSocket."""
    try:
        obs = get_obs_connection()
        result = obs.send_command("get_version", {})
        logger.info(f"test_obs_connection result: {result}")
        return json.dumps({"status": "success" if result["success"] else "error", "message": result["message"]})
    except Exception as e:
        logger.error(f"Test OBS connection failed: {e}")
        return json.dumps({"status": "error", "message": str(e)})

mcp.prompt = """
To manage OBS Studio for YouTube video recording, use these tools:
- `switch_scene(scene_name: str)`: Switch to a specific scene.
- `start_streaming()`: Start streaming to the configured platform.
- `stop_streaming()`: Stop the current stream.
- `start_recording()`: Start recording a video.
- `stop_recording()`: Stop recording and save the video.
- `toggle_source_visibility(scene_name: str, source_name: str, enabled: bool)`: Show or hide a source in a scene.
- `add_display_capture(scene_name: str, source_name: str)`: Add a display capture source to share your desktop screen.
- `set_source_position(scene_name: str, source_name: str, x: int, y: int, scale_x: float, scale_y: float)`: Reposition or resize a source in a scene.
- `get_scene_list()`: Retrieve a list of all scenes in OBS Studio.
- `test_obs_connection()`: Test the connection to OBS WebSocket.
Start by testing the connection, then set up your scene with a display capture for screen sharing, adjust positions if needed, and manage recording.
"""
logger.info("MCP prompt set")

if __name__ == "__main__":
    logger.info("Starting FastMCP server on port 8000")
    mcp.run()
    logger.info("FastMCP server stopped")
