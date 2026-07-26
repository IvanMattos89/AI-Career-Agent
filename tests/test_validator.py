from pathlib import Path

from sped_validator.core import split_sped_line, validate_file


def test_split_sped_line():
    assert split_sped_line("|0001|0|\n") == ["0001", "0"]
    assert split_sped_line("0001|0|") == []


def test_valid_minimal_file(tmp_path: Path):
    sped = tmp_path / "ok.txt"
    sped.write_text(
        "|0000|019|0|01012026|31012026|EMPRESA TESTE|12345678000199|SP|123456789012|3550308||A|0|\n"
        "|0001|0|\n"
        "|0990|2|\n"
        "|9990|1|\n"
        "|9999|5|\n",
        encoding="latin-1",
    )

    report = validate_file(sped)

    assert report.ok
    assert report.registers["0000"] == 1


def test_invalid_cst_is_error(tmp_path: Path):
    sped = tmp_path / "bad.txt"
    sped.write_text(
        "|0000|019|0|01012026|31012026|EMPRESA TESTE|12345678000199|SP|123456789012|3550308||A|0|\n"
        "|0001|0|\n"
        "|0990|2|\n"
        "|C001|0|\n"
        "|C190|999|5102|18,00|100,00|0,00|18,00|0,00|0,00|0,00||\n"
        "|C990|3|\n"
        "|9990|1|\n"
        "|9999|8|\n",
        encoding="latin-1",
    )

    report = validate_file(sped)

    assert not report.ok
    assert any(issue.code == "CST" for issue in report.errors)
