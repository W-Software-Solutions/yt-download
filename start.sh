#!/bin/bash

apt-get update && apt-get install -y ffmpeg

streamlit run main.py --server.port $PORT --server.enableCORS false
