"""WebSocket 连接管理器

单会话架构下，所有连接共享同一工作目录。
当前保留 session_id 参数以向后兼容，未来可以简化。
"""
from fastapi import WebSocket
from typing import Dict, List
import json

class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, session_id: str, websocket: WebSocket):
        """建立 WebSocket 连接"""
        await websocket.accept()
        if session_id not in self.active_connections:
            self.active_connections[session_id] = []
        self.active_connections[session_id].append(websocket)

    def disconnect(self, session_id: str, websocket: WebSocket):
        """断开连接"""
        if session_id in self.active_connections:
            if websocket in self.active_connections[session_id]:
                self.active_connections[session_id].remove(websocket)
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]

    async def send_to_session(self, session_id: str, message: dict):
        """向会话的所有连接发送消息"""
        if session_id in self.active_connections:
            disconnected = []
            for connection in self.active_connections[session_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    print(f"Error sending to websocket: {e}")
                    disconnected.append(connection)

            # 清理断开的连接
            for conn in disconnected:
                self.disconnect(session_id, conn)

    async def broadcast(self, message: dict):
        """广播消息到所有连接"""
        for session_id in list(self.active_connections.keys()):
            await self.send_to_session(session_id, message)

    async def close_all(self):
        """关闭所有连接"""
        for session_id, connections in list(self.active_connections.items()):
            for connection in connections:
                try:
                    await connection.close()
                except Exception:
                    pass
        self.active_connections.clear()

    def get_active_sessions(self) -> List[str]:
        """获取所有活跃的会话 ID"""
        return list(self.active_connections.keys())
