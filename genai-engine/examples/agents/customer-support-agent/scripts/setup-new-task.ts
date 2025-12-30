/**
 * Setup New Customer Support Agent Task
 * 
 * This script creates a complete new customer support agent task with:
 * - A new task
 * - 5 prompts (from bootstrap data, tagged as production)
 * - 3 LLM evals (from bootstrap data)
 * - 2 transforms (from bootstrap data)
 * - 3 continuous evals with transforms (from bootstrap data)
 * - Test questions dataset
 * 
 * It uses the bootstrap data extracted from an existing task.
 * 
 * Usage:
 *   node run-setup-new-task.js <task-name>
 * 
 * Example:
 *   node run-setup-new-task.js "Demo Customer Support Agent"
 */

import fs from "fs/promises";
import path from "path";
import axios from "axios";

const BOOTSTRAP_DIR = path.join(__dirname, "bootstrap-data");

interface PromptData {
  name: string;
  messages: any[];
  model_name: string;
  model_provider: string;
  config?: any;
  tools?: any[];
  variables?: string[];
}

interface LLMEvalData {
  name: string;
  instructions: string;
  model_name: string;
  model_provider: string;
  config?: any;
  variables?: string[];
}

interface TransformData {
  id: string;
  name: string;
  description?: string;
  definition: any;
}

interface ContinuousEvalData {
  name: string;
  description: string;
  llm_eval_name: string;
  llm_eval_version: number;
  transform_id: string;
}

interface SetupResult {
  taskId: string;
  taskName: string;
  prompts: { [name: string]: { version: number } };
  llmEvals: { [name: string]: { version: number } };
  transforms: { [oldId: string]: { newId: string; name: string } };
  continuousEvals: { [name: string]: { id: string } };
  datasets: { [name: string]: { id: string; versionId: string } };
}

// Create axios instance with auth
function getApiClient() {
  return axios.create({
    baseURL: process.env.ARTHUR_BASE_URL,
    headers: {
      Authorization: `Bearer ${process.env.ARTHUR_API_KEY}`,
    },
  });
}

async function loadBootstrapData() {
  console.log("Loading bootstrap data...\n");
  
  const promptsPath = path.join(BOOTSTRAP_DIR, "prompts.json");
  const llmEvalsPath = path.join(BOOTSTRAP_DIR, "llm-evals.json");
  const transformsPath = path.join(BOOTSTRAP_DIR, "transforms.json");
  const continuousEvalsPath = path.join(BOOTSTRAP_DIR, "continuous-evals.json");
  const datasetsPath = path.join(BOOTSTRAP_DIR, "datasets.json");
  const questionsPath = path.join(BOOTSTRAP_DIR, "test-questions.json");
  
  const [promptsData, llmEvalsData, transformsData, continuousEvalsData, datasetsData, questionsData] = await Promise.all([
    fs.readFile(promptsPath, "utf-8").then(JSON.parse),
    fs.readFile(llmEvalsPath, "utf-8").then(JSON.parse),
    fs.readFile(transformsPath, "utf-8").then(JSON.parse),
    fs.readFile(continuousEvalsPath, "utf-8").then(JSON.parse),
    fs.readFile(datasetsPath, "utf-8").then(JSON.parse),
    fs.readFile(questionsPath, "utf-8").then(JSON.parse),
  ]);
  
  console.log(`✓ Loaded ${Object.keys(promptsData).length} prompt templates`);
  console.log(`✓ Loaded ${Object.keys(llmEvalsData).length} LLM eval definitions`);
  console.log(`✓ Loaded ${Object.keys(transformsData).length} transform definitions`);
  console.log(`✓ Loaded ${continuousEvalsData.length} continuous eval definitions`);
  console.log(`✓ Loaded ${datasetsData.length} datasets`);
  console.log(`✓ Loaded ${questionsData.questions.length} test questions\n`);
  
  return { promptsData, llmEvalsData, transformsData, continuousEvalsData, datasetsData, questionsData };
}

async function createTask(apiClient: any, taskName: string): Promise<string> {
  console.log("1. Creating new task...");
  
  const response = await apiClient.post(`/api/v2/tasks`, {
    name: taskName,
    is_agentic: true,
  });
  
  const taskId = response.data.id;
  
  console.log(`   ✓ Created task: ${taskName}`);
  console.log(`   ✓ Task ID: ${taskId}\n`);
  
  return taskId;
}

async function createPrompts(
  apiClient: any,
  taskId: string,
  promptsData: { [key: string]: PromptData }
): Promise<{ [name: string]: { version: number } }> {
  console.log("2. Creating prompts...");
  
  const results: { [name: string]: { version: number } } = {};
  
  for (const [promptName, promptData] of Object.entries(promptsData)) {
    try {
      console.log(`   Creating: ${promptName}...`);
      
      const promptRequest = {
        messages: promptData.messages,
        model_name: promptData.model_name,
        model_provider: promptData.model_provider,
        config: promptData.config || null,
        tools: promptData.tools || null,
      };
      
      // Create the prompt
      const response = await apiClient.post(
        `/api/v1/tasks/${taskId}/prompts/${promptName}`,
        promptRequest
      );
      
      const version = response.data.version;
      results[promptName] = { version };
      
      console.log(`   ✓ Created ${promptName} (version ${version})`);
      console.log(`      Model: ${promptData.model_provider}/${promptData.model_name}`);
      
      // Tag as production
      await apiClient.put(
        `/api/v1/tasks/${taskId}/prompts/${promptName}/versions/${version}/tags`,
        { tag: "production" }
      );
      
      console.log(`   ✓ Tagged as 'production'`);
      
    } catch (error: any) {
      console.error(`   ✗ Error creating ${promptName}:`, error.message || error);
      throw error;
    }
  }
  
  console.log(`   ✓ All prompts created and tagged\n`);
  return results;
}

async function createLLMEvals(
  apiClient: any,
  taskId: string,
  llmEvalsData: { [key: string]: LLMEvalData }
): Promise<{ [name: string]: { version: number } }> {
  console.log("3. Creating LLM evals...");
  
  const results: { [name: string]: { version: number } } = {};
  
  if (Object.keys(llmEvalsData).length === 0) {
    console.log(`   ⚠️  No LLM evals to create\n`);
    return results;
  }
  
  for (const [evalName, evalData] of Object.entries(llmEvalsData)) {
    try {
      console.log(`   Creating: ${evalName}...`);
      
      const evalRequest = {
        instructions: evalData.instructions,
        model_name: evalData.model_name,
        model_provider: evalData.model_provider,
        config: evalData.config || null,
      };
      
      const response = await apiClient.post(
        `/api/v1/tasks/${taskId}/llm_evals/${evalName}`,
        evalRequest
      );
      
      const version = response.data.version;
      results[evalName] = { version };
      
      console.log(`   ✓ Created ${evalName} (version ${version})`);
      console.log(`      Model: ${evalData.model_provider}/${evalData.model_name}`);
      console.log(`      Variables: ${evalData.variables?.join(', ') || 'none'}`);
      
    } catch (error: any) {
      console.error(`   ✗ Error creating ${evalName}:`, error.message || error);
      console.error(`      Details:`, error.response?.data || error.message);
      throw error;
    }
  }
  
  console.log(`   ✓ All LLM evals created\n`);
  return results;
}

async function createTransforms(
  apiClient: any,
  taskId: string,
  transformsData: { [oldId: string]: TransformData }
): Promise<{ [oldId: string]: { newId: string; name: string } }> {
  console.log("4. Creating transforms...");
  
  const results: { [oldId: string]: { newId: string; name: string } } = {};
  
  if (Object.keys(transformsData).length === 0) {
    console.log(`   ⚠️  No transforms to create\n`);
    return results;
  }
  
  for (const [oldId, transformData] of Object.entries(transformsData)) {
    try {
      console.log(`   Creating: ${transformData.name}...`);
      
      const transformRequest = {
        name: transformData.name,
        description: transformData.description || null,
        definition: transformData.definition,
      };
      
      const response = await apiClient.post(
        `/api/v1/tasks/${taskId}/traces/transforms`,
        transformRequest
      );
      
      const newId = response.data.id;
      results[oldId] = { newId, name: transformData.name };
      
      console.log(`   ✓ Created ${transformData.name}`);
      console.log(`      Old ID: ${oldId}`);
      console.log(`      New ID: ${newId}`);
      console.log(`      Variables: ${transformData.definition.variables?.length || 0}`);
      
    } catch (error: any) {
      console.error(`   ✗ Error creating ${transformData.name}:`, error.message || error);
      console.error(`      Details:`, error.response?.data || error.message);
      throw error;
    }
  }
  
  console.log(`   ✓ All transforms created\n`);
  return results;
}

async function createContinuousEvals(
  apiClient: any,
  taskId: string,
  continuousEvalsData: ContinuousEvalData[],
  llmEvalsResults: { [name: string]: { version: number } },
  transformsResults: { [oldId: string]: { newId: string; name: string } }
): Promise<{ [name: string]: { id: string } }> {
  console.log("5. Creating continuous evals...");
  
  const results: { [name: string]: { id: string } } = {};
  
  if (continuousEvalsData.length === 0) {
    console.log(`   ⚠️  No continuous evals to create\n`);
    return results;
  }
  
  for (const contEval of continuousEvalsData) {
    try {
      console.log(`   Creating: ${contEval.name}...`);
      console.log(`      LLM Eval: ${contEval.llm_eval_name}`);
      
      // Get the new transform ID
      const transformMapping = transformsResults[contEval.transform_id];
      if (!transformMapping) {
        throw new Error(`Transform ${contEval.transform_id} not found in mappings`);
      }
      
      console.log(`      Transform: ${transformMapping.name} (${transformMapping.newId})`);
      
      const contEvalRequest = {
        name: contEval.name,
        description: contEval.description || "",
        llm_eval_name: contEval.llm_eval_name,
        llm_eval_version: contEval.llm_eval_version,
        transform_id: transformMapping.newId,
      };
      
      const response = await apiClient.post(
        `/api/v1/tasks/${taskId}/continuous_evals`,
        contEvalRequest
      );
      
      const contEvalId = response.data.id;
      results[contEval.name] = { id: contEvalId };
      
      console.log(`   ✓ Created (ID: ${contEvalId})`);
      
    } catch (error: any) {
      console.error(`   ✗ Error creating ${contEval.name}:`, error.message || error);
      console.error(`      Details:`, error.response?.data || error.message);
      throw error;
    }
  }
  
  console.log(`   ✓ All continuous evals created\n`);
  return results;
}

async function createDatasets(
  apiClient: any,
  taskId: string,
  datasetsData: any[]
): Promise<{ [name: string]: { id: string; versionId: string } }> {
  console.log("6. Creating datasets...");
  
  const results: { [name: string]: { id: string; versionId: string } } = {};
  
  if (datasetsData.length === 0) {
    console.log(`   ⚠️  No datasets to create\n`);
    return results;
  }
  
  for (const datasetData of datasetsData) {
    try {
      console.log(`   Creating: ${datasetData.name}...`);
      
      // Create the dataset
      const datasetRequest = {
        name: datasetData.name,
        description: datasetData.description || "",
        metadata: datasetData.metadata || null,
      };
      
      const datasetResponse = await apiClient.post(
        `/api/v2/tasks/${taskId}/datasets`,
        datasetRequest
      );
      
      const datasetId = datasetResponse.data.id;
      console.log(`      ✓ Created dataset (ID: ${datasetId})`);
      
      // Create the dataset version with rows
      if (datasetData.version && datasetData.version.rows) {
        console.log(`      Creating version with ${datasetData.version.rows.length} rows...`);
        
        // Transform the rows data from response format to request format
        // The response format already has the correct structure: [{ column_name, column_value }]
        const rowsData = datasetData.version.rows.map((row: any) => ({
          data: row.data  // row.data is already in the correct format
        }));
        
        const versionRequest = {
          rows_to_add: rowsData,
          rows_to_delete: [],
          rows_to_update: [],
        };
        
        const versionResponse = await apiClient.post(
          `/api/v2/datasets/${datasetId}/versions`,
          versionRequest
        );
        
        const versionId = versionResponse.data.id;
        console.log(`      ✓ Created version (ID: ${versionId})`);
        console.log(`      ✓ Added ${rowsData.length} rows`);
        
        results[datasetData.name] = { id: datasetId, versionId: versionId };
      } else {
        results[datasetData.name] = { id: datasetId, versionId: "" };
      }
      
    } catch (error: any) {
      console.error(`   ✗ Error creating ${datasetData.name}:`, error.message || error);
      console.error(`      Details:`, error.response?.data || error.message);
      throw error;
    }
  }
  
  console.log(`   ✓ All datasets created\n`);
  return results;
}

async function main() {
  console.log("Customer Support Agent Task Setup");
  console.log("==================================\n");
  
  // Get task name from command line arguments
  const taskName = process.argv[2];
  
  if (!taskName) {
    console.error("Error: Task name is required");
    console.error("Usage: node run-setup-new-task.js <task-name>");
    console.error('Example: node run-setup-new-task.js "Demo Customer Support Agent"');
    process.exit(1);
  }
  
  console.log(`Task Name: ${taskName}`);
  console.log(`Base URL: ${process.env.ARTHUR_BASE_URL}\n`);
  
  // Check bootstrap data exists
  try {
    await fs.access(BOOTSTRAP_DIR);
  } catch (error) {
    console.error(`Error: Bootstrap data not found at ${BOOTSTRAP_DIR}`);
    console.error("Please run 'node run-bootstrap-extract.js' first to extract the bootstrap data.");
    process.exit(1);
  }
  
  // Load bootstrap data
  const { promptsData, llmEvalsData, transformsData, continuousEvalsData, datasetsData, questionsData } = await loadBootstrapData();
  
  // Create API client
  const apiClient = getApiClient();
  
  // Create all components
  const result: SetupResult = {
    taskId: "",
    taskName: taskName,
    prompts: {},
    llmEvals: {},
    transforms: {},
    continuousEvals: {},
    datasets: {},
  };
  
  try {
    // 1. Create task
    result.taskId = await createTask(apiClient, taskName);
    
    // 2. Create prompts
    result.prompts = await createPrompts(apiClient, result.taskId, promptsData);
    
    // 3. Create LLM evals
    result.llmEvals = await createLLMEvals(apiClient, result.taskId, llmEvalsData);
    
    // 4. Create transforms
    result.transforms = await createTransforms(apiClient, result.taskId, transformsData);
    
    // 5. Create continuous evals (depends on LLM evals and transforms)
    result.continuousEvals = await createContinuousEvals(
      apiClient, 
      result.taskId, 
      continuousEvalsData,
      result.llmEvals,
      result.transforms
    );
    
    // 6. Create datasets
    result.datasets = await createDatasets(apiClient, result.taskId, datasetsData);
    
  } catch (error) {
    console.error("\n❌ Setup failed:", error);
    process.exit(1);
  }
  
  // Print summary
  console.log("==================================");
  console.log("✅ Setup Complete!");
  console.log("==================================\n");
  
  console.log("Summary:");
  console.log(`  Task Name: ${result.taskName}`);
  console.log(`  Task ID: ${result.taskId}`);
  console.log("");
  
  if (Object.keys(result.prompts).length > 0) {
    console.log(`  Prompts created: ${Object.keys(result.prompts).length}`);
    Object.entries(result.prompts).forEach(([name, info]) => {
      console.log(`    - ${name} (v${info.version})`);
    });
    console.log("");
  }
  
  if (Object.keys(result.llmEvals).length > 0) {
    console.log(`  LLM Evals created: ${Object.keys(result.llmEvals).length}`);
    Object.entries(result.llmEvals).forEach(([name, info]) => {
      console.log(`    - ${name} (v${info.version})`);
    });
    console.log("");
  }
  
  if (Object.keys(result.transforms).length > 0) {
    console.log(`  Transforms created: ${Object.keys(result.transforms).length}`);
    Object.entries(result.transforms).forEach(([oldId, info]) => {
      console.log(`    - ${info.name} (${info.newId})`);
    });
    console.log("");
  }
  
  if (Object.keys(result.continuousEvals).length > 0) {
    console.log(`  Continuous Evals created: ${Object.keys(result.continuousEvals).length}`);
    Object.entries(result.continuousEvals).forEach(([name, info]) => {
      console.log(`    - ${name} (${info.id})`);
    });
    console.log("");
  }
  
  if (Object.keys(result.datasets).length > 0) {
    console.log(`  Datasets created: ${Object.keys(result.datasets).length}`);
    Object.entries(result.datasets).forEach(([name, info]) => {
      console.log(`    - ${name} (${info.id})`);
    });
    console.log("");
  }
  
  console.log("Next steps:");
  console.log(`  1. Update your .env file with the new task ID:`);
  console.log(`     ARTHUR_TASK_ID=${result.taskId}`);
  console.log("");
  console.log(`  2. Run the test harness to verify:`);
  console.log(`     node run-test.js`);
  console.log("");
  
  // Save result to file for reference
  const resultPath = path.join(__dirname, "setup-result.json");
  await fs.writeFile(resultPath, JSON.stringify(result, null, 2));
  console.log(`Setup details saved to: ${resultPath}`);
  console.log("==================================");
}

// Run the setup
main().catch((error) => {
  console.error("Fatal error in setup script:", error);
  process.exit(1);
});

