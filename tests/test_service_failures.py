import inspect
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

from overleaf_mcp.models.overleaf_session import OverleafSession
from overleaf_mcp.services.overleaf.history import OverleafHistoryError, OverleafHistoryService
from overleaf_mcp.services.overleaf.project import OverleafProjectError, OverleafProjectService
from overleaf_mcp.services.overleaf.review import OverleafReviewError, OverleafReviewService


ARGUMENTS = {
    "session": OverleafSession(cookies={"sid": "x"}, csrf_token="csrf", email="x@y.z", created_at=datetime.now(timezone.utc)),
    "project_id": "project", "name": "name", "template": "none", "pathname": "main.tex",
    "from_version": 1, "to_version": 2, "version": 2, "comment": "label", "doc_id": "doc",
    "change_ids": ["change"], "thread_id": "thread", "content": "message", "enabled": True,
    "compiler": "xelatex", "root_doc_id": "doc", "main_bibliography_doc_id": "bib",
    "spell_check_language": "en", "image_name": "texlive", "before": 3, "min_count": 2,
}


class ErrorResponse:
    status_code = 500
    text = "server error"
    content = b"server error"
    def json(self): return {"error": "server error"}


class ServiceFailureContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_all_public_project_history_and_review_calls_reject_server_errors(self):
        client = SimpleNamespace(
            get=AsyncMock(return_value=ErrorResponse()), post=AsyncMock(return_value=ErrorResponse()),
            delete=AsyncMock(return_value=ErrorResponse()),
        )
        cases = [
            (OverleafProjectService(client), OverleafProjectError),
            (OverleafHistoryService(client), OverleafHistoryError),
            (OverleafReviewService(client), OverleafReviewError),
        ]
        for service, error_type in cases:
            for name, method in inspect.getmembers(service, inspect.iscoroutinefunction):
                if name.startswith("_"):
                    continue
                kwargs = {
                    parameter: ARGUMENTS[parameter]
                    for parameter in inspect.signature(method).parameters
                    if parameter in ARGUMENTS
                }
                with self.subTest(service=type(service).__name__, method=name):
                    with self.assertRaises(error_type):
                        await method(**kwargs)


if __name__ == "__main__":
    unittest.main()
