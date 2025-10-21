#!/bin/bash
# Run tests with coverage reporting

poetry run pytest \
    --cov=utils \
    --cov=whatsappbeacon \
    --cov-branch \
    --cov-report=term-missing:skip-covered \
    --cov-report=html \
    --cov-report=xml \
    --cov-fail-under=80 \
    "$@"