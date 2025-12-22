import nextJest from 'next/jest';

const createJestConfig = nextJest({ dir: './' });

const customJestConfig = {
  testEnvironment: 'node',
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/src/$1',
  },
  testPathIgnorePatterns: [
    '<rootDir>/node_modules/',
    '<rootDir>/.next/',
    '<rootDir>/src/components/',
  ],
  collectCoverageFrom: ['src/utils/**/*.{js,jsx,ts,tsx}', '!src/**/*.d.ts'],
};

export default createJestConfig(customJestConfig);
