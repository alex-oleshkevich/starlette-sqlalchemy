#!/usr/bin/env bash

pytest --cov starlette_sqlalchemy --cov-report=term-missing tests/
