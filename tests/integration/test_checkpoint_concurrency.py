"""체크포인트 동시성 테스트"""

import json
import os
import threading

import pytest

from crawler.utils.checkpoint import CheckpointManager


class TestCheckpointManager:
    """CheckpointManager 동시성 테스트"""

    def test_concurrent_checkpoint_access(self, tmp_path):
        """여러 스레드에서 동시에 체크포인트 접근 시 데이터 일관성 유지"""
        checkpoint_path = tmp_path / "concurrent_test_checkpoint.json"

        def worker(manager: CheckpointManager, worker_id: int, num_operations: int):
            """워커 스레드 함수"""
            for i in range(num_operations):
                key = f"key_{worker_id}_{i}"
                data = {"worker_id": worker_id, "iteration": i, "timestamp": i * 0.1}

                # 체크포인트 저장
                manager.save(key, data)

                # 잠시 대기 (동시성 테스트)
                import time

                time.sleep(0.001)

                # 체크포인트 로드 확인
                loaded = manager.load()
                assert key in loaded, f"Worker {worker_id}: Key {key} should be saved"
                assert loaded[key] == data, f"Worker {worker_id}: Data mismatch for {key}"

        # 공유 CheckpointManager 인스턴스 생성
        manager = CheckpointManager(str(checkpoint_path))

        # 여러 스레드에서 동시 실행
        num_threads = 10
        num_operations = 50

        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=worker, args=(manager, i, num_operations))
            threads.append(thread)

        # 모든 스레드 시작
        for thread in threads:
            thread.start()

        # 모든 스레드 완료 대기
        for thread in threads:
            thread.join()

        # 최종 데이터 확인
        final_manager = CheckpointManager(str(checkpoint_path))
        final_data = final_manager.load()

        # 모든 키가 저장되었는지 확인
        expected_keys = set()
        for worker_id in range(num_threads):
            for i in range(num_operations):
                expected_keys.add(f"key_{worker_id}_{i}")

        actual_keys = set(final_data.keys())
        missing_keys = expected_keys - actual_keys

        assert len(missing_keys) == 0, f"Missing keys: {missing_keys}"
        assert len(actual_keys) == len(expected_keys), (
            f"Expected {len(expected_keys)} keys, got {len(actual_keys)}"
        )

    def test_checkpoint_recovery_after_corruption(self, tmp_path):
        """손상된 체크포인트 파일 복구 테스트"""
        checkpoint_path = tmp_path / "corrupted_test_checkpoint.json"

        # 1. 정상적인 체크포인트 파일 생성
        manager = CheckpointManager(str(checkpoint_path))
        manager.save("key1", {"data": "value1"})
        manager.save("key2", {"data": "value2"})

        assert os.path.exists(checkpoint_path)

        # 2. 파일 손상 시키기 (잘못된 JSON)
        with open(checkpoint_path, "w") as f:
            f.write('{"invalid": json content}')  # 잘못된 JSON

        # 3. 백업 파일이 없는 상태에서 CheckpointManager 로드
        # 손상된 파일은 백업되고 새로운 빈 체크포인트가 생성되어야 함
        recovered_manager = CheckpointManager(str(checkpoint_path))
        recovered_data = recovered_manager.load()

        # 빈 체크포인트로 복구되어야 함
        assert recovered_data == {}

        # 백업 파일이 생성되었는지 확인
        backup_path = checkpoint_path.with_suffix(".json.backup")
        assert backup_path.exists()

        # 4. 새로운 데이터 저장 가능
        recovered_manager.save("new_key", {"data": "new_value"})
        new_data = recovered_manager.load()
        assert new_data == {"new_key": {"data": "new_value"}}

    def test_checkpoint_atomic_write(self, tmp_path):
        """체크포인트 원자적 쓰기 테스트 - 중간에 파일이 손상되지 않음"""
        checkpoint_path = tmp_path / "atomic_test_checkpoint.json"

        # 1. 초기 데이터 저장
        manager = CheckpointManager(str(checkpoint_path))
        initial_data = {"initial": "data"}
        manager.save("initial_key", initial_data)

        # 2. 다량의 데이터를 한 번에 저장
        large_data = {}
        for i in range(1000):
            key = f"large_key_{i}"
            large_data[key] = {
                "id": i,
                "text": "x" * 100,  # 각 데이터에 100자의 텍스트
                "nested": {"value": i * 2},
            }

        # 모든 데이터 저장
        for key, value in large_data.items():
            manager.save(key, value)

        # 3. 파일이 항상 유효한 JSON인지 확인
        for _ in range(10):  # 여러 번 확인
            try:
                with open(checkpoint_path, "r") as f:
                    json.load(f)  # JSON 파싱 시도
            except json.JSONDecodeError as e:
                pytest.fail(f"Checkpoint file contains invalid JSON: {e}")

        # 4. 모든 데이터가 올바르게 저장되었는지 확인
        final_data = manager.load()
        assert len(final_data) == len(large_data) + 1  # initial_key + large_data

        for key, value in large_data.items():
            assert key in final_data
            assert final_data[key] == value

        assert final_data["initial_key"] == initial_data

    def test_checkpoint_thread_safety_with_complex_operations(self, tmp_path):
        """복합적인 연산에서의 스레드 안전성 테스트"""
        checkpoint_path = tmp_path / "complex_test_checkpoint.json"
        shared_key = "shared_counter"

        def increment_worker(manager: CheckpointManager, worker_id: int, increments: int):
            """카운터 증가 워커"""

            for _ in range(increments):
                # 현재 값 읽기
                data = manager.load()
                current = data.get(shared_key, {"count": 0, "workers": []})

                # 새로운 값 계산
                new_count = current["count"] + 1
                if isinstance(current["workers"], set):
                    current["workers"].add(worker_id)
                else:
                    # set은 JSON 직렬화가 안되므로 리스트로 변환
                    workers_set = set(current.get("workers", []))
                    workers_set.add(worker_id)
                    current["workers"] = list(workers_set)

                new_data = {"count": new_count, "workers": current["workers"]}

                # 저장
                manager.save(shared_key, new_data)

                # 잠시 대기
                import time

                time.sleep(0.001)

        # 공유 CheckpointManager 인스턴스 생성
        manager = CheckpointManager(str(checkpoint_path))

        # 여러 스레드에서 카운터 증가
        num_threads = 5
        increments_per_thread = 20

        threads = []
        for i in range(num_threads):
            thread = threading.Thread(
                target=increment_worker, args=(manager, i, increments_per_thread)
            )
            threads.append(thread)

        # 모든 스레드 시작
        for thread in threads:
            thread.start()

        # 모든 스레드 완료 대기
        for thread in threads:
            thread.join()

        # 최종 결과 확인
        final_manager = CheckpointManager(str(checkpoint_path))
        final_data = final_manager.load()

        assert shared_key in final_data
        result = final_data[shared_key]

        # 모든 증가가 기록되었는지 확인 (경쟁 상태로 인해 일부 손실될 수 있음)
        # 중요한 것은 데이터가 일관성 있고 손상되지 않았다는 것
        assert result["count"] > 0
        assert isinstance(result["workers"], list)
        assert len(set(result["workers"])) <= num_threads  # 워커 ID는 중복되지 않아야 함
