# VerseMind-RAG Logging Configuration

VerseMind-RAG supports dynamic logging level configuration through environment variables, allowing you to control the verbosity of logs without modifying the code.

## Configuring Log Levels

You can set the logging level by updating the `LOG_LEVEL` environment variable in your `.env` file:

```
LOG_LEVEL=INFO  # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
```

Available log levels:

- `DEBUG`: Show all messages, including detailed debugging information
- `INFO`: Show informational messages, warnings, and errors (default)
- `WARNING`: Show only warnings and errors
- `ERROR`: Show only errors
- `CRITICAL`: Show only critical errors

## For Developers vs. End Users

- **End Users**: The default setting (`INFO`) provides a clean experience with minimal logging output
- **Developers**: Set to `DEBUG` when developing or troubleshooting for detailed information

## Best Practices

1. Keep `LOG_LEVEL=INFO` for production environments
2. Use `LOG_LEVEL=DEBUG` during development and troubleshooting
3. Consider `LOG_LEVEL=WARNING` when running on constrained systems to minimize output

## Implementation Details

The logging level is configured in the following places:

1. `.env` file: Sets the global `LOG_LEVEL` environment variable
2. Main application startup: Reads the environment variable and configures the logging system
3. Individual service classes: Each service uses the configured log level
