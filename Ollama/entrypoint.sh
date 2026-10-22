#!/bin/sh
set -e
/bin/ollama serve &
sleep 2
ollama pull llama3.1:8b
wait
