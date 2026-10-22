import unittest

from overleaf_mcp.services.overleaf.compile_log import parse_compile_log


class CompileLogTests(unittest.TestCase):
    def test_parses_errors_and_warnings(self):
        entries = parse_compile_log(
            "chapters/intro.tex:17: Undefined control sequence.\n"
            "LaTeX Warning: Citation `missing' undefined on input line 23.\n"
            "Package hyperref Warning: Token not allowed.\n"
        )

        self.assertEqual(
            [(entry.level, entry.file, entry.line, entry.message) for entry in entries],
            [
                ("error", "chapters/intro.tex", 17, "Undefined control sequence."),
                ("warning", None, 23, "Citation `missing' undefined"),
                ("warning", None, None, "[hyperref] Token not allowed."),
            ],
        )

    def test_ignores_unrecognised_lines(self):
        self.assertEqual(parse_compile_log("This is pdfTeX\nOutput written on main.pdf\n"), [])


if __name__ == "__main__":
    unittest.main()
