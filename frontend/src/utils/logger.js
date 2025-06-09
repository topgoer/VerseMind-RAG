/**
 * Logger utility for VerseMind-RAG frontend
 * Provides logging functionality that respects LOG_LEVEL from environment variables
 */

// Get log level from environment variables - default to 'INFO' if not set
const LOG_LEVEL = import.meta.env.VITE_LOG_LEVEL || 'INFO';

// Debug: Log the current log level setting
console.log('🔍 Logger Debug: VITE_LOG_LEVEL =', import.meta.env.VITE_LOG_LEVEL);
console.log('🔍 Logger Debug: Effective LOG_LEVEL =', LOG_LEVEL);

// Define log levels and their priorities
const LOG_LEVELS = {
  DEBUG: 0,
  INFO: 1,
  WARNING: 2,
  ERROR: 3,
  CRITICAL: 4
};

/**
 * Logger class that handles logging based on configured log level
 */
class Logger {
  constructor(module) {
    this.module = module;
    this.currentLevel = LOG_LEVELS[LOG_LEVEL] !== undefined ? LOG_LEVELS[LOG_LEVEL] : LOG_LEVELS.INFO;
    
    // Debug: Log logger initialization
    console.log(`🔍 Logger [${module}] initialized with level: ${LOG_LEVEL} (numeric: ${this.currentLevel})`);
  }

  /**
   * Format log message with timestamp and module name
   */
  _formatMessage(message) {
    return `[${this.module}] ${message}`;
  }

  /**
   * Log debug messages - only shown when LOG_LEVEL is DEBUG
   */
  debug(message, ...args) {
    if (this.currentLevel <= LOG_LEVELS.DEBUG) {
      console.debug(this._formatMessage(message), ...args);
    }
  }

  /**
   * Log informational messages - shown when LOG_LEVEL is INFO or lower
   */
  info(message, ...args) {
    if (this.currentLevel <= LOG_LEVELS.INFO) {
      console.info(this._formatMessage(message), ...args);
    }
  }

  /**
   * Log warning messages - shown when LOG_LEVEL is WARNING or lower
   */
  warn(message, ...args) {
    if (this.currentLevel <= LOG_LEVELS.WARNING) {
      console.warn(this._formatMessage(message), ...args);
    }
  }

  /**
   * Log error messages - shown when LOG_LEVEL is ERROR or lower
   */
  error(message, ...args) {
    if (this.currentLevel <= LOG_LEVELS.ERROR) {
      console.error(this._formatMessage(message), ...args);
    }
  }

  /**
   * Log critical errors - always shown
   */
  critical(message, ...args) {
    console.error(`CRITICAL ${this._formatMessage(message)}`, ...args);
  }
}

/**
 * Create and return a logger instance for the specified module
 */
export function getLogger(module) {
  return new Logger(module);
}

// Default logger
const logger = new Logger('App');

export default logger;
