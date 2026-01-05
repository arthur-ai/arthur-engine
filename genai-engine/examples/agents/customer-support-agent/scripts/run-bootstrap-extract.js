#!/usr/bin/env node
/**
 * Bootstrap Extract Runner
 * 
 * This script loads environment variables from .env and runs the bootstrap extract script.
 */

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

// Load environment variables from .env file
const envPath = path.join(__dirname, '..', '.env');
if (fs.existsSync(envPath)) {
  console.log('Loading environment from .env file...\n');
  require('dotenv').config({ path: envPath });
} else {
  console.warn('Warning: .env file not found at', envPath);
  console.warn('Make sure environment variables are set.\n');
}

// Check required environment variables
const required = ['ARTHUR_BASE_URL', 'ARTHUR_API_KEY', 'ARTHUR_TASK_ID'];
const missing = required.filter(key => !process.env[key]);

if (missing.length > 0) {
  console.error('Error: Missing required environment variables:');
  missing.forEach(key => console.error(`  - ${key}`));
  process.exit(1);
}

// Run the TypeScript file using tsx
const scriptPath = path.join(__dirname, 'bootstrap-extract.ts');
console.log('Running bootstrap extract script...\n');

const child = spawn('npx', ['tsx', scriptPath], {
  stdio: 'inherit',
  env: process.env,
  shell: true
});

child.on('exit', (code) => {
  process.exit(code || 0);
});

