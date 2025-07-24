## Onboarding Context Generation

We follow the [LLMSTxt formatting standard](https://llmstxt.org/) and offer two flexible tools to generate onboarding contexts:

### Data Sources

- **GeneratedOnBoardings**: If your repository already contains pre-generated onboarding data, our tools will automatically detect and use it.
- **Website Demo Fallback**: If no generated data is available in the repo, you can create it on-the-fly via our [interactive demo](https://www.codeboarding.org/demo).

### Available Tools

1. **`get_onboarding_context_with_code`**  
   Produces a comprehensive context **including** code references. Ideal for large repositories (contexts >100K tokens).

2. **`get_onboarding_context_without_code`**  
   Produces a streamlined context **excluding** code references. Useful when you need a lean summary.

### Tool Arguments

| Argument       | Description                                                                                      |
| -------------- | ------------------------------------------------------------------------------------------------ |
| `repo_name`    | Repository identifier (must match an entry in GeneratedOnBoardings).                             |
| `token_budget` | Maximum allowed tokens in the returned context. Contexts exceeding this limit will be truncated. |

### Quick Start

#### 1. Using the Python Script

```bash
python utils/read_repo.py --repo_name <YOUR_REPO> --token_budget <MAX_TOKENS>
```

#### 2. Running via Claude Desktop (Local MCP)

1. **Install Claude Desktop** if you haven’t already.  
2. **Configure your MCP server** by editing `~/Library/Application Support/Claude/claude_desktop_config.json`:

    ```json
    {
      "mcpServers": {
        "codeboarding_mcp": {
          "command": "uv",
          "args": [
            "--directory",
            "/Users/<YOUR_USER>/Documents/github_folder/CodeBoarding-MCP",
            "run",
            "main.py"
          ]
        }
      }
    }
    ```

3. **Launch the MCP**:

    ```bash
    fastmcp run main.py
    ```



TODO: ngrok and setup config for remote use. 