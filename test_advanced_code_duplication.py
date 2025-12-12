"""고급 코드 중복 감지 테스트

실제 코드 내용을 비교하여 더 정확하게 중복을 찾습니다.
"""

import ast
import difflib
import re
from pathlib import Path
from dataclasses import dataclass
from collections import defaultdict
from typing import List, Tuple


@dataclass
class CodeBlock:
    """코드 블록 정보"""

    file_path: str
    start_line: int
    end_line: int
    content: List[str]
    node_type: str
    name: str


class AdvancedDuplicateDetector:
    """고급 중복 감지기"""

    def __init__(self, min_lines: int = 3, similarity_threshold: float = 0.8):
        self.min_lines = min_lines
        self.similarity_threshold = similarity_threshold
        self.code_blocks: List[CodeBlock] = []
        self.duplicates: List[Tuple[CodeBlock, CodeBlock, float]] = []

    def analyze_file(self, filepath: Path) -> None:
        """파일을 분석하여 코드 블록 추출"""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()

            # 함수와 클래스 추출
            tree = ast.parse("".join(lines))

            # 함수 추출
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    block = CodeBlock(
                        file_path=str(filepath),
                        start_line=node.lineno,
                        end_line=node.end_lineno if hasattr(node, "end_lineno") else node.lineno,
                        content=lines[node.lineno - 1 : node.end_lineno],
                        node_type="function",
                        name=node.name,
                    )
                    self.code_blocks.append(block)

                elif isinstance(node, ast.ClassDef):
                    block = CodeBlock(
                        file_path=str(filepath),
                        start_line=node.lineno,
                        end_line=node.end_lineno if hasattr(node, "end_lineno") else node.lineno,
                        content=lines[node.lineno - 1 : node.end_lineno],
                        node_type="class",
                        name=node.name,
                    )
                    self.code_blocks.append(block)

        except Exception as e:
            print(f"Error analyzing {filepath}: {e}")

    def find_duplicates(self) -> List[Tuple[CodeBlock, CodeBlock, float]]:
        """중복 코드 찾기"""
        # 같은 타입과 비슷한 이름의 코드 블록 비교
        blocks_by_type_name = defaultdict(list)

        for block in self.code_blocks:
            # 파일명 기준으로 그룹화 (다른 파일 간의 중복만 찾기)
            file_type = Path(block.file_path).parent.name
            key = f"{file_type}:{block.node_type}:{block.name}"
            blocks_by_type_name[key].append(block)

        # 비슷한 이름의 블록들 비교
        for blocks in blocks_by_type_name.values():
            if len(blocks) > 1:
                self._compare_blocks(blocks)

        # 다른 이름이지만 비슷한 구조의 블록들도 비교
        self._find_structural_duplicates()

        return self.duplicates

    def _compare_blocks(self, blocks: List[CodeBlock]) -> None:
        """블록들 간의 중복 비교"""
        for i in range(len(blocks)):
            for j in range(i + 1, len(blocks)):
                block1, block2 = blocks[i], blocks[j]

                # 다른 파일인 경우에만 비교
                if block1.file_path != block2.file_path:
                    similarity = self._calculate_similarity(block1, block2)
                    if similarity >= self.similarity_threshold:
                        self.duplicates.append((block1, block2, similarity))

    def _find_structural_duplicates(self) -> None:
        """구조적으로 유사한 블록 찾기"""
        # 특정 패턴을 가진 함수들 찾기
        pattern_blocks = defaultdict(list)

        for block in self.code_blocks:
            # 코드 내용에서 패턴 추출
            normalized = self._normalize_code("".join(block.content))

            # 키워드 기반으로 그룹화
            if "self." in normalized:
                if "def _validate" in normalized:
                    pattern_blocks["_validate"].append(block)
                elif "def _normalize" in normalized:
                    pattern_blocks["_normalize"].append(block)
                elif "def _make_request" in normalized:
                    pattern_blocks["_make_request"].append(block)
                elif "writer" in normalized or "csv" in normalized:
                    pattern_blocks["csv_writer"].append(block)

        # 패턴 그룹 내에서 중복 찾기
        for blocks in pattern_blocks.values():
            if len(blocks) > 1:
                # 다른 파일에서 찾은 블록들만 비교
                file_blocks = defaultdict(list)
                for block in blocks:
                    file_blocks[block.file_path].append(block)

                if len(file_blocks) > 1:
                    all_blocks = [b for fb in file_blocks.values() for b in fb]
                    self._compare_blocks(all_blocks)

    def _normalize_code(self, code: str) -> str:
        """코드 정규화 (공백, 주석, 변수명 등 정리)"""
        # 주석 제거
        code = re.sub(r"#.*$", "", code, flags=re.MULTILINE)

        # 문자열 리터럴 제거
        code = re.sub(r'["\'][^"\']*["\']', '"STR"', code)

        # 공백 정규화
        code = re.sub(r"\s+", " ", code)

        # 변수명 정규화 (self.xxx -> self.attr, local_var -> var)
        code = re.sub(r"self\.\w+", "self.attr", code)
        code = re.sub(r"\b[a-z_][a-z0-9_]*\b(?!\s*\()", "var", code)

        return code.strip()

    def _calculate_similarity(self, block1: CodeBlock, block2: CodeBlock) -> float:
        """두 코드 블록의 유사도 계산"""
        # 라인 수 비교
        len1 = len(block1.content)
        len2 = len(block2.content)

        if len1 < self.min_lines or len2 < self.min_lines:
            return 0.0

        # 정규화된 코드로 비교
        norm1 = self._normalize_code("".join(block1.content))
        norm2 = self._normalize_code("".join(block2.content))

        # 시퀀스 유사도 계산
        similarity = difflib.SequenceMatcher(None, norm1, norm2).ratio()

        # 라인 수 차이에 대한 페널티
        size_penalty = min(len1, len2) / max(len1, len2)

        return similarity * size_penalty


def test_advanced_duplicate_detection():
    """고급 중복 감지 테스트 실행"""
    detector = AdvancedDuplicateDetector(min_lines=5, similarity_threshold=0.7)
    base_dir = Path(__file__).parent

    # 분석할 파일들
    files_to_analyze = [
        base_dir / "src/crawler/api/hogangnono_client.py",
        base_dir / "src/crawler/api/memory_efficient_client.py",
        base_dir / "src/crawler/writers/base_csv_writer.py",
        base_dir / "src/crawler/writers/hogangnono_csv_writer.py",
        base_dir / "src/crawler/writers/dataclass_csv_writer.py",
        base_dir / "src/crawler/writers/memory_optimized_csv_writer.py",
        base_dir / "src/crawler/validators/apartment_validator.py",
        base_dir / "src/crawler/validators/csv_validator.py",
        base_dir / "src/crawler/validators/data_validator.py",
    ]

    # 파일 분석
    for filepath in files_to_analyze:
        if filepath.exists():
            print(f"\n분석 중: {filepath}")
            detector.analyze_file(filepath)

    # 중복 찾기
    duplicates = detector.find_duplicates()

    # 결과 출력
    print(f"\n\n총 발견된 중복 코드: {len(duplicates)}개\n")

    # 유사도 순으로 정렬
    duplicates.sort(key=lambda x: x[2], reverse=True)

    for dup in duplicates[:10]:  # 상위 10개만 출력
        block1, block2, similarity = dup

        print(f"\n유사도: {similarity:.2f}")
        print(
            f"파일1: {Path(block1.file_path).name}:{block1.start_line}-{block1.end_line} ({block1.node_type} {block1.name})"
        )
        print(
            f"파일2: {Path(block2.file_path).name}:{block2.start_line}-{block2.end_line} ({block2.node_type} {block2.name})"
        )

        # 코드 일부 출력
        code1 = "".join(block1.content[:3]).strip()
        code2 = "".join(block2.content[:3]).strip()
        print(f"코드1: {code1[:100]}...")
        print(f"코드2: {code2[:100]}...")

    # 중복 패턴 분석
    print("\n\n중복 패턴 분석:")
    pattern_count = defaultdict(int)
    for block1, block2, _ in duplicates:
        pattern = f"{block1.node_type}:{block1.name}"
        pattern_count[pattern] += 1

    print("\n가장 많이 중복된 패턴:")
    for pattern, count in sorted(pattern_count.items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"  {pattern}: {count}회 중복")

    return len(duplicates) > 0


if __name__ == "__main__":
    has_duplicates = test_advanced_duplicate_detection()
    print(f"\n\n{'중복 코드 발견!' if has_duplicates else '중복 코드 없음'}")
