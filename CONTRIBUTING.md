# Contributing to Chess Bot API

Thank you for considering contributing to this project. This document outlines the process and guidelines for contributing.

## How to Contribute

### Reporting Bugs

If you find a bug, please open an issue with:
- Clear description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Your environment (OS, Python version, Node version)

### Suggesting Features

Feature suggestions are welcome. Please open an issue with:
- Clear description of the feature
- Use case and benefits
- Potential implementation approach

### Pull Requests

1. Fork the repository
2. Create a new branch for your feature or bugfix
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. Make your changes
4. Test your changes thoroughly
5. Commit with clear, descriptive messages
6. Push to your fork
7. Open a pull request with description of changes

## Development Setup

### Backend

```bash
cd Backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Run tests:
```bash
pytest
```

### Frontend

```bash
cd Frontend
npm install
npm run dev
```

Run linting:
```bash
npm run lint
```

## Code Style

### Python
- Follow PEP 8 style guide
- Use type hints where appropriate
- Add docstrings for functions and classes
- Keep functions focused and small

### JavaScript/React
- Use ES6+ features
- Follow functional programming patterns
- Use meaningful variable names
- Keep components simple and reusable

## Testing

- Write tests for new features
- Ensure all tests pass before submitting PR
- Aim for good test coverage

### Backend Tests

```bash
cd Backend
pytest tests/
```

### Frontend Tests

```bash
cd Frontend
npm run test  # If test script is configured
```

## Commit Messages

Write clear commit messages:
- Use present tense ("Add feature" not "Added feature")
- Keep first line under 50 characters
- Add detailed description if needed

Example:
```
Add transposition table to bot v2

Implement a hash table to store previously evaluated positions,
improving search performance by avoiding redundant calculations.
```

## Code Review Process

1. Maintainers will review your PR
2. Address any feedback or requested changes
3. Once approved, your PR will be merged
4. Your contribution will be credited

## Questions

If you have questions, feel free to:
- Open an issue for discussion
- Contact the maintainers

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
