#!/usr/bin/env node
/**
 * Setup New Task Runner
 * 
 * This script loads environment variables from .env and runs the setup script
 * to create a new customer support agent task.
 * 
 * Usage: node run-setup-new-task.js <task-name>
 */

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

// Check if task name was provided
if (process.argv.length < 3) {
  console.error('Error: Task name is required');
  console.error('Usage: node run-setup-new-task.js <task-name>');
  console.error('Example: node run-setup-new-task.js "Demo Customer Support Agent"');
  process.exit(1);
}

const taskName = process.argv[2];

// Load environment variables from .env file
const envPath = path.join(__dirname, '..', '.env');
if (fs.existsSync(envPath)) {
  console.log('Loading environment from .env file...\n');
  require('dotenv').config({ path: envPath });
} else {
  console.warn('Warning: .env file not found at', envPath);
  console.warn('Make sure environment variables are set.\n');
}

// Check required environment variables (don't need ARTHUR_TASK_ID since we're creating a new task)
const required = ['ARTHUR_BASE_URL', 'ARTHUR_API_KEY'];
const missing = required.filter(key => !process.env[key]);

if (missing.length > 0) {
  console.error('Error: Missing required environment variables:');
  missing.forEach(key => console.error(`  - ${key}`));
  process.exit(1);
}

// Run the TypeScript file using tsx
const scriptPath = path.join(__dirname, 'setup-new-task.ts');
console.log(`Setting up new task: "${taskName}"\n`);

const child = spawn('npx', ['tsx', scriptPath, taskName], {
  stdio: 'inherit',
  env: process.env,
  shell: true
});

child.on('exit', (code) => {
  process.exit(code || 0);
});

