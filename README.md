# concertfinder_script

[클래식 콘서트 검색 엔진](https://www.classical-concert-kr.info/)의 데이터를 담당하는 스크립트입니다.\
공연예술통합전산망 [KOPIS API](https://kopis.or.kr/por/cs/openapi/openApiInfo.do?menuId=MNU_00074)를 이용하여 공연의 메타데이터와 포스터를 얻고 OpenAI의 ChatGPT API를 사용하여 작곡가, 연주곡 등을 추출합니다.

TODO
- [x] [pythonanywhere](www.pythonanywhere.com)에서 웹사이트 호스팅하기
- [x] CronJob 으로 매일 새로운 콘서트 정보 입력
- [x] sqlite3에서 postgresql으로 이동하기 
- [x] Docker 환경 구축하기 [Docker image](https://hub.docker.com/layers/niceweather/concertfinder/1.0.2/images/sha256-d3f1e35b258eea46e498c2ea02465d4cee57637f09311e11da96458af7ec28fa?context=repo)
- [ ] 미디어 파일을 Amazon S3 에 저장하여 관리
- [ ] Amazon EC2와 Docker 이미지를 이용해 웹사이트 호스팅하기
