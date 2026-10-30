# MISSION 5-1 — Mini Redis

[GitHub 저장소](https://github.com/tjdgns6427-ops/MISSION-5-1) · [자동 테스트](https://github.com/tjdgns6427-ops/MISSION-5-1/actions)

해시맵, 이중 연결 리스트, 최소 힙을 직접 구현한 Python CLI 키·값 저장소입니다. 문자열 저장, UTF-8 바이트 기준 메모리 제한, LRU 자동 제거, TTL 만료를 지원합니다.

## 실행

Python 3.8 이상이 필요하며 외부 패키지는 사용하지 않습니다. 이 README가 있는 폴더에서 실행합니다.

```console
python -m mini_redis
```

또는 `python main.py`를 실행합니다. 대화형 실행에서는 `mini-redis>` 프롬프트가 표시됩니다. `exit`, `quit`, 입력 종료(EOF)로 종료할 수 있습니다. 파일이나 파이프로 입력하면 프롬프트 없이 결과만 출력합니다.

```console
python -m unittest discover -s tests -v
```

## 명령어

명령어 이름과 `CONFIG SET maxmemory`, `INFO memory`의 하위 명령은 대소문자를 구분하지 않습니다. 키와 값은 대소문자를 구분합니다. 공백을 포함한 값과 빈 문자열은 큰따옴표로 감쌉니다.

| 명령어 | 동작 및 반환값 |
| --- | --- |
| `SET key value` | 저장 후 `OK`. 기존 TTL을 지우고 LRU의 최근 위치로 이동 |
| `GET key` | 값은 `"value"`, 없거나 만료되었으면 `(nil)`. 조회 성공 시에만 LRU 갱신 |
| `DEL key` | 삭제하면 `(integer) 1`, 없으면 `(integer) 0` |
| `EXISTS key` | 존재하면 `(integer) 1`, 없으면 `(integer) 0` |
| `DBSIZE` | 만료되지 않은 키 수를 `(integer) N`으로 출력 |
| `KEYS` | 전체 키를 번호가 붙은 배열로 출력. 순서는 보장하지 않음 |
| `CONFIG SET maxmemory bytes` | 메모리 상한 설정 후 `OK`. `0`은 무제한 |
| `INFO memory` | `used_memory`, `maxmemory`, `evicted_keys` 출력 |
| `EXPIRE key seconds` | 만료 설정에 성공하면 `(integer) 1`, 키가 없으면 `(integer) 0` |
| `TTL key` | 남은 초를 내림한 정수. 만료 설정이 없으면 `-1`, 키가 없으면 `-2` |

```console
mini-redis> SET greeting "안녕하세요 Redis"
OK
mini-redis> GET greeting
"안녕하세요 Redis"
mini-redis> SET empty ""
OK
mini-redis> TTL greeting
(integer) -1
mini-redis> EXPIRE greeting 0
(integer) 1
mini-redis> GET greeting
(nil)
```

숫자 인수는 부호를 포함할 수 있는 64비트 정수입니다. `maxmemory`는 0 이상이어야 하며, `EXPIRE`의 초가 0 이하이면 즉시 삭제합니다. TTL은 실제 경과 시간에 따라 줄어들므로 `EXPIRE key 3` 직후 `TTL key`는 보통 `2` 또는 `3`으로 표시될 수 있습니다.

## 메모리와 LRU 예시

메모리는 다음 식으로 계산합니다. Python 객체, 버킷, 포인터 등 자료구조 자체의 크기는 포함하지 않습니다.

```text
used_memory = Σ (len(key.encode("utf-8")) + len(value.encode("utf-8")))
```

```console
mini-redis> CONFIG SET maxmemory 30
OK
mini-redis> SET user:1 "Alice"
OK
mini-redis> SET user:2 "Bob"
OK
mini-redis> SET user:3 "Charlie"
OK
mini-redis> GET user:1
(nil)
mini-redis> INFO memory
used_memory:22
maxmemory:30
evicted_keys:1
```

각 항목은 11, 9, 13바이트입니다. 합계 33바이트가 제한을 넘으므로 가장 오래 사용하지 않은 `user:1`을 제거해 22바이트가 됩니다. `GET`과 `SET`에 성공했을 때만 최근 사용 순서를 바꿉니다. `EXISTS`, `TTL`, `KEYS` 등의 조회는 순서를 바꾸지 않습니다.

단일 키와 값만으로 상한을 넘으면 `SET`은 OOM 오류를 반환합니다. 기존 키를 덮어쓰려던 경우에도 기존 값, TTL, 최근 사용 순서를 유지합니다. 명령 실행 전 이미 만료된 키를 정리하는 동작은 정상적으로 수행됩니다. 상한을 낮추는 `CONFIG SET maxmemory`는 즉시 LRU 제거를 수행합니다. TTL에 의한 삭제는 `evicted_keys`에 포함하지 않습니다.

## 오류 예시

```console
mini-redis> GET
(error) ERR wrong number of arguments for 'GET' command
mini-redis> HELLO
(error) ERR unknown command 'HELLO'
mini-redis> CONFIG SET maxmemory abc
(error) ERR value is not an integer or out of range
mini-redis> CONFIG SET maxmemory 1
OK
mini-redis> SET key value
(error) OOM command not allowed when used_memory > 'maxmemory'
```

잘못된 입력은 오류를 출력하고 다음 명령을 계속 받습니다.

## 구조와 제출 확인

```text
mini_redis/
  store.py                 # 데이터, LRU, TTL, 메모리 정책
  commands.py              # 입력 파싱, 인수 검증, Redis 스타일 출력
  cli.py                   # REPL과 표준 입력 처리
  structures/
    dynamic_array.py       # 용량을 2배로 늘리는 동적 배열
    linked_list.py         # 이중 연결 리스트
    hash_map.py            # FNV-1a 해시와 체이닝
    min_heap.py            # 인덱스를 관리하는 TTL 최소 힙
tests/                     # 자료구조·명령·경계 조건·CLI 검증
docs/                      # 설계 설명, 요구사항 대응표, 보너스 문서
.github/workflows/         # GitHub Actions 테스트
```

- [설계와 시간 복잡도](docs/ARCHITECTURE.md)
- [요구사항 대응표](docs/REQUIREMENTS.md)
- [스택·큐·덱 개념과 활용](docs/STACK_QUEUE_DEQUE.md)
- [검증 결과](docs/TEST_RESULTS.md)

저장소의 핵심 구현은 `dict`, `set`, `collections`, `heapq`로 대체하지 않았습니다. 자료구조의 내부 배열은 고정 길이 Python 리스트를 확보한 뒤 인덱스로 접근합니다. 명령 파싱과 결과 목록은 일반 문자열·리스트로 전달합니다. 네트워크 서버, 디스크 영속성, Redis 복합 자료형, 멀티스레딩은 과제 범위에 포함하지 않습니다.

GitHub Actions는 저장소에 변경 사항을 올리면 Python 3.8과 3.13에서 자동 테스트를 실행하도록 구성되어 있습니다. GitHub에서 Actions 실행 결과를 확인할 수 있습니다.
