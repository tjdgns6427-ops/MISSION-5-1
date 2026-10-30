# 요구사항 대응표

첨부된 과제의 필수 기능과 추가 구현의 위치를 정리했습니다. 실행 방법과 출력 예시는 [README](../README.md), 구현 원리와 비용은 [ARCHITECTURE](ARCHITECTURE.md)를 참고합니다.

| 요구사항 | 구현 위치 | 확인 방법 |
| --- | --- | --- |
| Python 3.8 이상, CLI 프로그램 | `main.py`, `mini_redis/__main__.py`, `mini_redis/cli.py` | `python -m mini_redis` |
| `prev`, `next`, `data` 노드 | `structures/linked_list.py` | 노드 연결과 양 끝 상태 테스트 |
| 리스트 앞·뒤 삽입·제거, 노드 제거·앞 이동 | `structures/linked_list.py` | 빈 리스트·단일 노드·중간 노드·연속 이동 테스트 |
| 리스트 삽입·삭제·이동 O(1) | `structures/linked_list.py` | 직접 노드 참조, 탐색 없는 포인터 갱신 |
| 직접 설계한 해시 함수와 체이닝 | `structures/hash_map.py` | UTF-8 FNV-1a, 같은 버킷 충돌 테스트 |
| 해시맵 `put/get/remove/contains/keys/size` | `structures/hash_map.py` | 교체·삭제·미존재·키 목록 테스트 |
| 로드 팩터 0.75 초과 시 버킷 2배 확장 | `structures/hash_map.py` | 확장 경계와 확장 후 값 보존 테스트 |
| 최소 힙 `push/pop/peek/size`와 heapify | `structures/min_heap.py` | 삽입·추출 순서와 위·아래 재정렬 테스트 |
| `(expire_at, key)` 만료 관리 | `structures/min_heap.py`, `store.py` | 같은 만료 시각·재설정·취소 테스트 |
| 문자열 명령 6개 | `commands.py`, `store.py` | `SET/GET/DEL/EXISTS/DBSIZE/KEYS` 출력 테스트 |
| 최대 메모리 설정과 상태 출력 | `commands.py`, `store.py` | `CONFIG SET maxmemory`, `INFO memory` 테스트 |
| UTF-8 키·값 바이트 합계 | `store.py` | 한글·빈 문자열·덮어쓰기·삭제 테스트 |
| 성공한 `GET/SET`에만 LRU 갱신 | `store.py` | 최근 사용 순서와 비갱신 명령 테스트 |
| 메모리 초과 시 오래된 키부터 제거 | `store.py` | 연속 제거, 상한 축소, 제거 횟수 테스트 |
| 단일 항목 상한 초과 시 OOM | `store.py`, `commands.py` | 신규 저장·기존 값 덮어쓰기 실패 테스트 |
| OOM 실패 시 기존 값과 TTL 유지 | `store.py` | 실패 후 값·TTL·LRU 상태 테스트 |
| `EXPIRE`, `TTL`과 즉시 만료 | `store.py`, `commands.py` | 가짜 시계로 경계 시각과 0·음수 테스트 |
| 없는 키·만료 키 처리 | `store.py` | `(nil)`, 0, TTL -2 및 전역 조회 테스트 |
| 덮어쓰기 시 TTL 초기화 | `store.py` | `EXPIRE` 후 `SET`, 이전 시각 경과 테스트 |
| 삭제 시 데이터·TTL·LRU 함께 정리 | `store.py`, `structures/min_heap.py` | 삭제 후 같은 키 재삽입 테스트 |
| Redis 스타일 성공·정수·배열·오류 출력 | `commands.py` | 명령별 문자열 출력 비교 |
| 미지원 명령·인수 개수·정수 오류 | `commands.py` | 오류 뒤 후속 정상 명령 실행 테스트 |
| 따옴표 문자열과 반복 입력 | `commands.py`, `cli.py` | 공백·빈 문자열·EOF·종료 명령 테스트 |
| `dict/set/collections`로 저장소 대체 금지 | `mini_redis/` 전체 | 사용자 정의 자료구조 재사용 및 소스 검토 |
| 독립 자료구조 모듈과 주석·docstring | `mini_redis/structures/` | 파일 분리와 핵심 클래스·메서드 설명 |
| GitHub 자동 검증 | `.github/workflows/` | push 또는 PR 후 Actions 결과 확인 |

위 표에서 `structures/`, `store.py`, `commands.py` 등의 경로는 모두 `mini_redis/` 아래를 뜻합니다. 테스트는 저장소 루트에서 아래 명령으로 실행합니다.

```console
python -m unittest discover -s tests -v
```

## 추가 구현

- 동적 배열: `append/get/set/remove`, 끝 항목 제거, 용량 2배 확장. 해시맵 버킷과 힙 저장소에 실제로 사용합니다.
- 스택·큐·덱 개념 문서: [STACK_QUEUE_DEQUE.md](STACK_QUEUE_DEQUE.md).
- 인덱스가 있는 TTL 힙: 타이머를 갱신·삭제할 때 오래된 항목을 물리적으로 제거합니다.

이진 트리 순회, BST, Pub/Sub는 선택 과제로 이번 구현에 포함하지 않았습니다. 네트워크 통신, 파일 영속성, 복합 자료형, 동시성 처리는 명시된 과제 범위에서 제외했습니다.
