# 1000year · 천년의신화 런처

Windows용 천년의신화 V1.070KR 런처. 게임 파일은 포함하지 않습니다.

## 실행

`dist/MythLauncher.exe`를 실행한 뒤 `MMyth.exe`가 있는 게임 폴더를 지정합니다. 빌드된 EXE에는 호환 DLL과 패치 레시피, 업데이트 설치 도구가 포함되어 있어 EXE 하나만 옮겨도 실행할 수 있습니다.

- 기본 설정: **1024×768 화면 확대**, 창 모드. 내부 렌더링과 전장 범위는 **640×480 그대로**입니다.
- 원본 640×480 출력 및 전체 화면(4:3 비율 유지) 선택.
- 화면 출력과 마우스 좌표를 cnc-ddraw에서 함께 변환합니다. HUD, 미니맵, 선택 사각형은 같은 비율로 표시됩니다.
- 시작할 때 GitHub 정식 릴리스를 확인하여 새 버전을 자동 다운로드·설치하고 재시작합니다. 설정에서 끌 수 있습니다. 인터넷 오류나 릴리스 없음은 게임 실행을 막지 않습니다.
- 게임 폴더의 `MMyth.exe`는 변경하지 않습니다. 원본 해시 및 수정 전후 바이트를 검증해 `MMyth.Portable.exe`를 생성합니다.
- 게임의 오래된 설치 경로 의존성을 없애고 현재 게임 폴더에서 읽습니다. 레지스트리를 바꾸거나 관리자 권한을 요구하지 않습니다. 오래된 시작 영상은 건너뜁니다.
- 최초 적용 전 `ddraw.dll`, `ddraw.ini`를 `.1000year-original`로 백업합니다. ‘원래 그래픽 복원’으로 돌아갈 수 있습니다. 게임 실행 중에는 적용하지 않습니다.
- 설정과 로그: `%LOCALAPPDATA%/1000year/`. 저장 게임은 원래 게임 폴더에 유지됩니다.

## 내부 1024×768 상태

**전장 시야를 넓히는 내부 해상도 지원은 미완료입니다.** 엔진 모드 변경을 실제로 시험했으나 512×480 지형 캐시와 고정 HUD 좌표 때문에 표시가 깨졌습니다. 따라서 런처에서는 이 시험 기능을 노출하지 않습니다. `analysis/hd-preview.json`은 개발 참고용이며 배포 패치가 아닙니다. 상세 분석과 추가 작업은 `analysis/RESOLUTION.md`에 있습니다.

## 빌드와 배포

Windows의 .NET Framework 4.x C# 컴파일러를 사용합니다. 별도 SDK 설치 없이 PowerShell에서:

```powershell
./scripts/build.ps1
./tests/Test-Installer.ps1
```

게임 파일이 있는 환경에서는 `tests/Run-Tests.ps1 -GameExe '게임폴더/MMyth.exe'`로 원본/패치 및 업데이트 검사를 실행합니다.

빌드 결과: `MythLauncher.exe`, 버전별 EXE, `MythLauncher.zip`, `MythLauncher.zip.sha256`. GitHub 저장소 `japanoxx-afk/1000year`의 정식 릴리스에 ZIP과 SHA256을 같은 이름으로 올리면 자동 업데이트 대상이 됩니다. 버전은 `src/Core.cs`의 `Version`을 올리고 태그 `vX.Y.Z`와 맞춥니다. 프리릴리스는 자동 설치하지 않습니다. ZIP 및 파일별 SHA256 검증, 설치 전 준비 확인, 기존 파일 백업, 실패 시 복구를 수행합니다. 게임/설정은 업데이트 대상에 포함하지 않습니다.

## 확인한 범위

실제 Windows에서 시작 업데이트 확인, 메뉴/시나리오 진입, 백제 첫 전장, 단일 유닛 선택, 드래그 다중 선택, 우클릭 이동을 확인했습니다. 자동 업데이트 설치/백업/손상 거부는 격리된 폴더에서 검사했습니다. 장시간 전투, 모든 시나리오, 멀티플레이, 모든 모니터/DPI 조합은 아직 검증하지 않았습니다.

참고 구현: 같은 작업공간의 아마게돈 `src/Updates.cs`, `scripts/apply-update.ps1`, `docs/hd-resolution-status.md`, 태조왕건 `src/updater.py`. 타 게임의 패치 주소는 재사용하지 않았습니다.

cnc-ddraw는 MIT 라이선스이며 `third-party/LICENSE.cnc-ddraw`를 동봉합니다.
