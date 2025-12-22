/* eslint-env jest */
// Mock implementation for the logger
const logger = {
  info: jest.fn(),
  error: jest.fn(),
  warn: jest.fn(),
  debug: jest.fn(),
};

export default logger;
