module.exports = { testDir: './tests', testMatch: '**/*.spec.cjs', timeout: 180000,
  workers: 1, retries: 0, reporter: 'list', outputDir: process.env.SHIYE_TEST_OUTPUT || 'test-results' };
