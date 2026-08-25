#!/bin/bash

ENDPOINTS=(
http://localhost:8000/health
http://localhost:8001/health
http://localhost:8002/health
)

for url in "${ENDPOINTS[@]}"
do
    if ! curl -fs "$url" >/dev/null
    then
        logger "[llama] FAILED $url"
        exit 1
    fi
done

exit 0
