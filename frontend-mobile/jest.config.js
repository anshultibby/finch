/** Jest config for unit tests (pure logic). Component/visual coverage lives in Playwright. */
module.exports = {
  preset: 'jest-expo',
  testMatch: ['**/tests/unit/**/*.test.ts?(x)'],
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/$1',
  },
};
