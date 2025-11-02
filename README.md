````markdown
# 🧩 프로젝트 모음 레포지토리

이 저장소는 서로 다른 목적의 Python 기반 실습 및 자동화 스크립트를 포함하고 있습니다.  
로컬 LLM 실험, Discord 봇, 그리고 엑셀 리포트 자동화를 다룹니다.

---

## 📘 레포지토리 개요

| 폴더명 | 설명 |
| --- | --- |
| **ch_13_ollama_llm_AI** | 로컬 Ollama 환경에서 **Gemma3 모델**을 호출하는 실험 스크립트와 **Streamlit 기반 미니 챗봇 앱**을 포함합니다. |
| **discord-AI** | **OpenWeather API**와 **RSS 피드**를 이용해 매일 아침 **날씨·뉴스 브리핑**을 전송하는 **Discord 봇**입니다. |
| **excel-auto** | 다양한 형태의 **매출 데이터를 정규화·검증·집계**하고, **월간 리포트 엑셀 파일과 시각화**를 자동으로 생성하는 CLI 도구입니다. |

---

## 🧠 1. Ollama LLM 실습 (ch_13_ollama_llm_AI)

### 주요 스크립트
- **`step_x.py`**  
  Gemma3 4B 모델에 사용자 질문을 전송하고, 대화 히스토리를 직접 관리하는 예제 코드입니다.  
  `requests` 또는 `subprocess`로 Ollama API에 쿼리를 보내며, 히스토리 로깅을 통해 문맥 유지 실험이 가능합니다.

- **`step_y.py`**  
  **Streamlit UI**를 이용한 대화형 챗봇 앱입니다.  
  `st.session_state`로 대화 내역을 보존하고, Ollama 응답을 UI에 실시간 출력합니다.

### 실행 요구 사항
- **Ollama 및 Gemma3 모델**이 로컬에 설치되어 있어야 합니다.  
- Streamlit 라이브러리 사용:  
  ```bash
  pip install streamlit
  streamlit run step_y.py
````

* 실행 전 Ollama 서버가 백그라운드에서 실행 중인지 반드시 확인합니다.

---

## 🤖 2. Discord 아침 브리핑 봇 (discord-AI)

### 주요 기능

* **OpenWeather API**로 현재 날씨를 조회하고, 환경 변수에 도시 또는 위도·경도를 설정합니다.
* **RSS 피드**(환경 변수 `FEEDS`로 지정)에서 최신 뉴스 헤드라인을 수집하고, 중복을 제거해 정리합니다.
* **Discord 임베드 메시지** 형태로 날씨 + Top 5 뉴스 링크를 묶어 **지정 채널로 자동 발송**합니다.
* **APScheduler**로 매일 **08:00 KST**에 자동 실행되며, 슬래시 커맨드 `/briefing`으로 수동 호출도 지원합니다.

### 실행 준비

1. `.env` 파일 또는 시스템 환경 변수에 다음을 설정합니다:

   ```
   DISCORD_TOKEN=디스코드_봇_토큰
   CHANNEL_ID=채널_ID
   OPENWEATHER_API_KEY=API_키
   FEEDS=RSS_URL1,RSS_URL2,...
   ```
2. 봇 실행:

   ```bash
   python morning_brief_bot.py
   ```

---

## 📊 3. 엑셀 자동 병합 및 리포트 (excel-auto)

### 동작 개요

* `merge_and_report.py`는 **`inbox/`** 폴더의 CSV·엑셀 파일을 읽어 **표준 컬럼명으로 정규화**합니다.
* 결측값·음수값 검증 후 월별 데이터를 집계하여 **리포트용 엑셀 파일과 시각화 그래프**를 생성합니다.

### 결과물

* **`output/`** 폴더 내에 다음 파일들이 생성됩니다:

  * `YYYY-MM_report.xlsx` – 월별 정제 데이터 및 제품/부서/일자별 요약 시트
  * `top_products.png`, `sales_trends.png` – 매출 상위 항목 및 추이 그래프
  * `run.log` – 처리 로그 파일

### 설정 및 실행

* **`config.yaml`**에서 기준월(`target_month`), 컬럼 매핑, 타입 변환, 검증 규칙, 차트 옵션 등을 정의합니다.
* 실행 명령:

  ```bash
  pip install -r requirements.txt
  python merge_and_report.py --month YYYY-MM
  ```

  (옵션 미지정 시 `config.yaml`의 `target_month` 값이 적용됩니다.)

---

## 🧩 공통 환경

* Python 3.10 이상
* 필수 패키지는 각 프로젝트별 `requirements.txt` 참고
* OS: Windows / macOS / Linux 호환

---

> 각 프로젝트는 독립적으로 실행 가능하며, 학습용·자동화 실습용으로 설계되었습니다.
> **AI 실험**, **봇 자동화**, **데이터 파이프라인 구성**을 모두 경험해볼 수 있습니다.

```
```
