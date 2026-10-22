import inspect
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from overleaf_mcp.models.entity import FileContent
from overleaf_mcp.tools import citation, config, editing, file, review


PARAMETERS = {
    "project_id": "project", "path": "main.tex", "query": "needle", "regex": False,
    "start_line": 1, "end_line": 2, "offset": 1, "limit": 1, "content": "content",
    "name": "renamed.tex", "destination_folder": "chapters", "url": "https://example.test/file",
    "find": "old", "replace": "new", "key": "citation", "compiler": "xelatex",
    "language": "en", "image_name": "texlive", "enabled": True, "change_ids": ["change"],
    "thread_id": "thread",
}


class UniversalComponent:
    def __init__(self):
        self.calls = {}

    def __getattr__(self, name):
        if name not in self.calls:
            result = FileContent(content="one\ntwo", type="doc") if name == "read_file" else []
            self.calls[name] = AsyncMock(return_value=result)
        return self.calls[name]


class ToolAdapterTests(unittest.IsolatedAsyncioTestCase):
    async def test_component_tool_modules_delegate_every_operation(self):
        files = UniversalComponent(); editing_component = UniversalComponent(); cfg = UniversalComponent()
        citations = UniversalComponent(); review_component = UniversalComponent(); comments = UniversalComponent()
        app = SimpleNamespace(
            overleaf_session=object(), files_component=files, editing_component=editing_component,
            config_component=cfg, citation_component=citations, review_component=review_component,
            comment_component=comments,
        )
        ctx = SimpleNamespace(lifespan_context={"app": app})

        skipped = {"read_file"}
        for module in (citation, config, editing, file, review):
            for name, function in inspect.getmembers(module, inspect.iscoroutinefunction):
                if name.startswith("_") or name in skipped:
                    continue
                kwargs = {parameter: PARAMETERS[parameter] for parameter in inspect.signature(function).parameters if parameter != "ctx"}
                with self.subTest(module=module.__name__, function=name):
                    await function(ctx, **kwargs)

        result = await file.read_file(ctx, "project", "main.tex", offset=2, limit=1)
        self.assertEqual(result.content, "two")
        with self.assertRaises(ValueError):
            await file.read_file(ctx, "project", "main.tex", offset=0)


if __name__ == "__main__":
    unittest.main()
