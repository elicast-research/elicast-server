# elicast-server

A backend server for elicast research.


## How to run

### Using dockerized environment (recommended)

Before you start, please ensure that these components are ready in the system:
- Docker

```bash
# run the server on http://0.0.0.0:8080 with 2 processes
HTTP_PORT=8080 CONFIG_PATH=configs/dev.py ./run.sh
```

### Using system python and ffmpeg

Before you start, please ensure that these components are ready in the system:
- Python 3.6 or above
- ffmpeg at `/usr/bin/ffmpeg`
- Docker

```bash
# prepare virtualenv
python3 -m venv venv
source venv/bin/activate

# install dependencies
pip install -r requirements.txt

# run the server on http://0.0.0.0:7822
CONFIG_PATH=configs/dev.py python3 server.py

# run the server on http://0.0.0.0:8008 with 2 processes
CONFIG_PATH=configs/dev.py gunicorn server:webserver.app -k aiohttp.worker.GunicornWebWorker -b :8080 -w 2 --access-logfile -
```


## API reference

### Elicast

- GET /elicast

    - List Elicasts in descending order of created timestamp.

    - Parameters

        - page(int; optional) -- Page number for list pagniation, `0 <= page`, default: 0
        - count(int; optional) -- Max. number for objects in a response, `1 <= count <= 100`, default: 20
        - teacher(string; optional) -- Filter by teacher name, `1 <= len(teacher) <= 64`, default: null

    - Request

        ```sh
        curl -i -X GET \
         'http://0.0.0.0:7822/elicast'
        ```

    - Response

        ```js
        {
          "elicasts":[
            {
              "id": 3,
              "created": 1503363045000,
              "title": "Hello",
              "teacher": null,
              "is_protected": true
            },
            {
              "id": 2,
              "created": 1503361314000,
              "title": "Hello2",
              "teacher": "jungkook",
              "is_protected": false
            }
          ]
        }
        ```


- PUT /elicast

    - Create a new elicast.

    - Parameters

        - title(string) -- Title of elicast, `1 <= len(title) <= 128`
        - ots(string) -- OTs of elicast, JSON-serialized list
        - voice_blobs(string) -- Voice of elicast, JSON-serialized list of data-URI-format string (~ 100MB)
        - teacher(string; optional) -- teacher name, `1 <= len(teacher) <= 64`, default: null

    - Request

        ```sh
        curl -i -X PUT \
           -H "Content-Type:application/x-www-form-urlencoded" \
           --data-urlencode "title=Hello2" \
           --data-urlencode 'ots=[ { "ts": 1 } ]' \
           --data-urlencode 'voice_blobs=["data:audio/webm;base64,asdf", "data:audio/webm;base64,qwer"]' \
         'http://0.0.0.0:7822/elicast'
        ```

    - Response

        ```js
        {
          "elicast":{
            "id": 2
          }
        }
        ```

- GET /elicast/`{elicast_id:[1-9]+\d*}`

    - Get the elicast.

    - Request

        ```sh
        curl -i -X GET \
         'http://0.0.0.0:7822/elicast/2'
        ```

    - Response

        ```js
        {
          "elicast":{
            "id": 2,
            "created": 1503361314000,
            "title": "Hello2",
            "ots": [ { "ts":1 } ],
            "voice_blobs": ["data:audio/webm;base64,asdf", "data:audio/webm;base64,qwer"],
            "teacher": "jungkook",
            "is_protected": false
          }
        }
        ```

- POST /elicast/`{elicast_id:[1-9]+\d*}`

    - Modify the elicast. If `elicast.is_protected === true`, the API returns 404 error.

    - Request/Response are same to `PUT /elicast`


- DELETE /elicast/`{elicast_id:[1-9]+\d*}`

    - Delete the elicast. If `elicast.is_protected === true`, the API returns 404 error.

    - Request

        ```sh
        curl -i -X DELETE \
         'http://0.0.0.0:7822/elicast/1'
        ```

    - Response

        ```js
        {
          "elicast":{
            "id": 1
          }
        }
        ```


### Code

- POST /code/run

    - Execute arbitary Python3.6 code.

    - Parameters

        - code(string) -- Python code to execute

    - Request

        ```sh
        curl -i -X POST \
           -H "Content-Type:application/x-www-form-urlencoded" \
           --data-urlencode 'code=print("hello world!"); assert(1 == 0)' \
         'http://0.0.0.0:7822/code/run'
        ```

    - Response

        ```js
        // `code_run.id` can be used for logging
        {
          "code_run": {
            "id": 1
          },
          "output": "hello world!\nTraceback (most recent call last):\n File \"/codefile.py\", line 1, in <module>\n print('hello world!'); assert(1 == 0)\nAssertionError\n",
          "exit_code": 1
        }
        ```

- POST /code/answer/`{elicast_id:[1-9]+\d*}`

    - Execute arbitray Python3.6 code in an exercise area.

    - Parameters

        - ex_id(string) -- The id of exercise the user is trying to solve
        - solve_ots(string) -- The ots written in the exercise area, JSON-serialized list
        - code(string) -- Python code to execute

    - Request

        ```sh
        curl -i -X POST \
           -H "Content-Type:application/x-www-form-urlencoded" \
           --data-urlencode 'ex_id=2' \
           --data-urlencode 'solve_ots=[ { "insertedText": "asdf" } ]' \
           --data-urlencode 'code=print("hello asdf!"); assert(1 == 0)' \
         'http://0.0.0.0:7822/code/answer/1'
        ```

    - Response

        ```js
        // `code_run_exercise.id` can be used for logging
        {
          "code_run_exercise": {
            "id": 5
          },
          "exit_code": 1
        }
        ```


### Audio

- POST /audio/split

    - Extract arbitray part of audio

    - Parameters

        - segments(string) -- List of parts consits of start/end timestamp, JSON-serialized list
        - audio_blobs(string) -- Original audio/webm files, JSON-serialized list of data-URI-format

    - Request

        ```sh
        # Return 0s ~ 1s part and .5s ~ 3s part of original audio
        curl -i -X POST \
           -H "Content-Type:application/x-www-form-urlencoded" \
           --data-urlencode 'segments=[[0, 1000],[500, 3000]]' \
           --data-urlencode 'audio_blobs=["data:audio/webm;base64,asdf", "data:audio/webm;base64,qwer"]' \
         'http://0.0.0.0:7822/audio/split'
        ```

    - Response

        ```js
        {
          "outputs": [
            "data:audio/webm;base64,asqw",
            "data:audio/webm;base64,dfgh"
          ]
        }
        ```

### Log

- POST /log/ticket

    - Get ticket for logging. The ticket is used to distinguish user session. The server records IP, "user-agent" header, and "referer" header of the request.

    - Parameters

        - name(string) -- The name of logger, 1 <= len(name) <= 64

    - Request

        ```sh
        curl -i -X POST \
           -H "Content-Type:application/x-www-form-urlencoded" \
           --data-urlencode 'name=test' \
         'http://0.0.0.0:7822/log/ticket'
        ```

    - Response

        ```js
        {
          "ticket": "c8c4b480-11a9-4714-9a36-c655bfa96c5c"
        }
        ```

- POST /log/submit

    - Submit any data to log.

    - Parameters

        - ticket(string) -- Ticket issued by `/log/ticket` API, `len(ticket) == 36`
        - data(string) -- Data to log, JSON-format

    - Request

        ```sh
        curl -i -X POST \
           -H "Content-Type:application/x-www-form-urlencoded" \
           --data-urlencode 'ticket=462ee55b-3f59-4b5f-8b67-aac1f0c6b36f' \
           --data-urlencode 'data={ "action": "try_ex", "code_run_exercise_id": 2 }' \
         'http://0.0.0.0:7822/log/submit'
        ```

    - Response

        ```js
        {
        }
        ```
