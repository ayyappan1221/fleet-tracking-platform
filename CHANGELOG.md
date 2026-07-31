# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.0] - Day 1 (Problem Statement Finalization)

### Added
- Problem_Statement.md with project scope, domain, entities, and user roles
- Basic FastAPI project structure (app/, tests/, docs/)
- PostgreSQL database configuration with SQLAlchemy 2.0
- User model with role-based access (manager, driver, mechanic)
- Authentication schemas (register, login, token response)
- Auth router with /register and /login endpoints
- JWT token creation and verification with python-jose
- Password hashing with bcrypt via passlib
- Environment-based configuration (.env.example)
- .gitignore for Python/PostgreSQL/IDE
- MIT License
- README v1 with setup and local run instructions
