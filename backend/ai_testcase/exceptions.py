class RagError(Exception):
    """本地 RAG / 生成失败。"""

    def __init__(self, message, status_code=500, payload=None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.payload = payload or {}
