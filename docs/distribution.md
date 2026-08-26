# Distribution

Every GitHub release contains the built wheel and source distribution. That gives a versioned install path without cloning the repository:

```bash
pip install https://github.com/dkharlanau/interface-as-code/releases/download/v0.3.0/interface_as_code-0.3.0-py3-none-any.whl
```

The repository also contains a PyPI Trusted Publishing workflow. It is intentionally manual until the PyPI project/account has a trusted publisher configured; this prevents a release from creating a red publish workflow or requiring a stored API token.

The reusable GitHub Action can be consumed through the stable major tag:

```yaml
- uses: dkharlanau/interface-as-code@v0
  with:
    path: interfaces
    fail-on: error
```
