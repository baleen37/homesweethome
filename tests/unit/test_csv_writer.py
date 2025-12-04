from pathlib import Path

from crawler.writers.csv_writer import CSVWriter


def test_csv_writer_creates_file(tmp_path: Path):
    output_file = tmp_path / "test.csv"
    writer = CSVWriter(output_file)
    data = [{"name": "test", "value": 123}]

    writer.write(data)

    assert output_file.exists()


def test_csv_writer_writes_header_and_rows(tmp_path: Path):
    output_file = tmp_path / "test.csv"
    writer = CSVWriter(output_file)
    data = [{"name": "item1", "price": 100}, {"name": "item2", "price": 200}]

    writer.write(data)

    content = output_file.read_text()
    lines = content.strip().split("\n")
    assert len(lines) == 3
    assert "name,price" in lines[0]
    assert "item1,100" in lines[1]


def test_csv_writer_creates_parent_directory(tmp_path: Path):
    output_file = tmp_path / "subdir" / "nested" / "test.csv"
    writer = CSVWriter(output_file)
    data = [{"key": "value"}]

    writer.write(data)

    assert output_file.exists()


def test_csv_writer_handles_empty_data(tmp_path: Path):
    output_file = tmp_path / "test.csv"
    writer = CSVWriter(output_file)

    writer.write([])

    assert not output_file.exists()


def test_csv_writer_append_mode(tmp_path: Path):
    output_file = tmp_path / "test.csv"
    writer = CSVWriter(output_file)
    data1 = [{"name": "item1", "value": 1}]
    data2 = [{"name": "item2", "value": 2}]

    writer.write(data1)
    writer.append(data2)

    content = output_file.read_text()
    lines = content.strip().split("\n")
    assert len(lines) == 3
