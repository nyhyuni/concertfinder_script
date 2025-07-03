# concertfinder_script

7/3/25\
This is a project I started to make it easier to find classical concerts in Korea. Right now, there isn’t really a site where you can look up concerts by composer or piece, so I wanted to build one. The site used to look like the screenshot below, and I recently picked it back up to improve how it works and looks. It’s private for now while I make some updates, but I plan to make it public again soon.\
In the meantime, this is the script I used to get concert metadata from [KOPIS API](https://kopis.or.kr/por/cs/openapi/openApiInfo.do?menuId=MNU_00074) and extract information. 

<img width="1015" alt="2" src="https://github.com/user-attachments/assets/e3fb7cfe-e9cd-45dd-986f-cbcba3aeaf3a" />
<img width="896" alt="1" src="https://github.com/user-attachments/assets/d95a420b-2d9e-4090-bb9b-e15687257358" />

---
클래식 콘서트 검색 엔진의 데이터를 처리하는 스크립트입니다.\
공연예술통합전산망에서 제공하는 [KOPIS API](https://kopis.or.kr/por/cs/openapi/openApiInfo.do?menuId=MNU_00074)를 통해 공연의 메타데이터와 포스터를 얻고 OpenAI의 ChatGPT API를 사용하여 작곡가, 연주곡 등을 추출합니다.

TODO
- [x] [pythonanywhere](https://www.pythonanywhere.com)에서 웹사이트 호스팅하기
- [x] CronJob 으로 매일 새로운 콘서트 정보 입력
- [x] sqlite3에서 postgresql으로 이동하기 
- [x] Docker 환경 구축하기 [Docker image](https://hub.docker.com/layers/niceweather/concertfinder/1.0.2/images/sha256-d3f1e35b258eea46e498c2ea02465d4cee57637f09311e11da96458af7ec28fa?context=repo)
- [ ] 미디어 파일을 Amazon S3 에 저장하여 관리
- [ ] Amazon EC2와 Docker 이미지를 이용해 웹사이트 호스팅하기
