import unittest

from overleaf_mcp.models.project_tree import (
    PathResolutionError,
    TreeEntity,
    TreeFolder,
    find_doc_path,
    flatten_docs,
    flatten_entities,
    path_segments,
    resolve_entity,
    resolve_entity_ref,
    resolve_folder,
)


def sample_tree() -> TreeFolder:
    return TreeFolder(
        id="root",
        name="root",
        docs=[TreeEntity(id="main", name="main.tex")],
        file_refs=[
            TreeEntity(
                id="refs",
                name="references.bib",
                linked_file_data={"provider": "zotero"},
            )
        ],
        folders=[
            TreeFolder(
                id="chapters",
                name="chapters",
                docs=[TreeEntity(id="intro", name="intro.tex")],
            )
        ],
    )


class ProjectTreeTests(unittest.TestCase):
    def setUp(self):
        self.tree = sample_tree()

    def test_flattens_docs_and_all_entities(self):
        self.assertEqual(flatten_docs(self.tree), [("main.tex", "main"), ("chapters/intro.tex", "intro")])
        self.assertEqual(
            flatten_entities(self.tree),
            [
                ("main.tex", "doc", "main"),
                ("references.bib", "file", "refs"),
                ("chapters/intro.tex", "doc", "intro"),
            ],
        )
        self.assertEqual(find_doc_path(self.tree, "intro"), "chapters/intro.tex")
        self.assertIsNone(find_doc_path(self.tree, "missing"))

    def test_resolves_folders_and_entities_with_normalised_paths(self):
        self.assertEqual(path_segments("//chapters///"), ["chapters"])
        self.assertEqual(resolve_folder(self.tree, "/chapters/").id, "chapters")
        self.assertEqual(resolve_entity(self.tree, "chapters/intro.tex"), ("doc", "intro"))
        entity_type, entity = resolve_entity_ref(self.tree, "references.bib")
        self.assertEqual(entity_type, "file")
        self.assertEqual(entity.linked_file_data, {"provider": "zotero"})

    def test_rejects_empty_and_unknown_paths(self):
        with self.assertRaisesRegex(PathResolutionError, "must not be empty"):
            resolve_entity(self.tree, "///")
        with self.assertRaisesRegex(PathResolutionError, "No such folder"):
            resolve_folder(self.tree, "missing")
        with self.assertRaisesRegex(PathResolutionError, "No such path"):
            resolve_entity(self.tree, "missing.tex")


if __name__ == "__main__":
    unittest.main()
