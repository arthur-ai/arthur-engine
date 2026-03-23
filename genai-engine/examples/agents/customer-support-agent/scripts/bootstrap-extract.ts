/**
 * Bootstrap Extract Script
 * 
 * This script extracts ALL data from an existing customer support agent task
 * and saves it to the bootstrap-data directory for use in creating new tasks.
 * 
 * It extracts:
 * - Task details
 * - All 5 prompts (plan, websearch, github, draft, review) with full templates
 * - All LLM evals with their configurations
 * - All continuous evals with their LLM evals and transforms
 * - Datasets (test questions)
 * 
 * NOTE: This script expects environment variables to be already loaded
 */

import fs from "fs/promises";
import path from "path";
import axios from "axios";

const PROMPT_NAMES = [
  "mastra-agent-support-plan",
  "mastra-agent-support-websearch",
  "mastra-agent-support-github",
  "mastra-agent-support-draft",
  "mastra-agent-support-review",
];

const BOOTSTRAP_DIR = path.join(__dirname, "bootstrap-data");

// Create axios instance with auth
function getApiClient() {
  return axios.create({
    baseURL: process.env.ARTHUR_BASE_URL,
    headers: {
      Authorization: `Bearer ${process.env.ARTHUR_API_KEY}`,
    },
  });
}

async function main() {
  console.log("Customer Support Agent Bootstrap Extract");
  console.log("========================================\n");

  const taskId = process.env.ARTHUR_TASK_ID;
  if (!taskId) {
    throw new Error("ARTHUR_TASK_ID environment variable is required");
  }

  console.log(`Task ID: ${taskId}`);
  console.log(`Base URL: ${process.env.ARTHUR_BASE_URL}`);
  console.log("");

  // Create bootstrap directory
  await fs.mkdir(BOOTSTRAP_DIR, { recursive: true });
  console.log(`✓ Created bootstrap directory: ${BOOTSTRAP_DIR}\n`);

  const apiClient = getApiClient();

  // 1. Extract task details
  console.log("1. Extracting task details...");
  let taskData: any;
  
  try {
    const taskResponse = await apiClient.get(`/api/v2/tasks/${taskId}`);
    taskData = taskResponse.data;
    
    await fs.writeFile(
      path.join(BOOTSTRAP_DIR, "task.json"),
      JSON.stringify(taskData, null, 2)
    );
    
    console.log(`   ✓ Task: ${taskData.name}`);
    console.log(`   ✓ Is Agentic: ${taskData.is_agentic}`);
    console.log(`   ✓ Saved to: task.json\n`);
  } catch (error) {
    console.error("   ✗ Error extracting task:", error);
    throw error;
  }

  // 2. Extract prompts
  console.log("2. Extracting prompts...");
  const prompts: any = {};
  
  for (const promptName of PROMPT_NAMES) {
    try {
      console.log(`   Fetching: ${promptName}...`);
      
      // Get the "production" version
      const promptResponse = await apiClient.get(
        `/api/v1/tasks/${taskId}/prompts/${promptName}/versions/tags/production`
      );
      
      const promptData = promptResponse.data;
      prompts[promptName] = {
        name: promptData.name,
        messages: promptData.messages,
        model_name: promptData.model_name,
        model_provider: promptData.model_provider,
        version: promptData.version,
        tags: promptData.tags,
        config: promptData.config || {},
        tools: promptData.tools || [],
        variables: promptData.variables || [],
      };
      
      console.log(`   ✓ ${promptName} (version ${promptData.version})`);
      console.log(`      Model: ${promptData.model_provider}/${promptData.model_name}`);
      console.log(`      Messages: ${promptData.messages.length}`);
      console.log(`      Tags: ${promptData.tags?.join(', ') || 'none'}`);
    } catch (error: any) {
      console.error(`   ✗ Error fetching ${promptName}:`, error.message || error);
      // Continue with other prompts even if one fails
    }
  }
  
  await fs.writeFile(
    path.join(BOOTSTRAP_DIR, "prompts.json"),
    JSON.stringify(prompts, null, 2)
  );
  console.log(`   ✓ Saved all prompts to: prompts.json\n`);

  // 3. Extract Continuous Evals (this will also get the LLM evals)
  console.log("3. Extracting continuous evals...");
  const continuousEvals: any[] = [];
  const llmEvalsMap: any = {};
  const transformsMap: any = {};
  
  try {
    // Get all continuous evals for the task
    const continuousEvalsResponse = await apiClient.get(
      `/api/v1/tasks/${taskId}/continuous_evals`
    );
    
    const continuousEvalsData = continuousEvalsResponse.data.evals || [];
    
    if (continuousEvalsData.length > 0) {
      console.log(`   Found ${continuousEvalsData.length} continuous eval(s)`);
      
      for (const contEval of continuousEvalsData) {
        console.log(`   Processing: ${contEval.name}...`);
        console.log(`      ID: ${contEval.id}`);
        console.log(`      LLM Eval: ${contEval.llm_eval_name} (v${contEval.llm_eval_version})`);
        console.log(`      Transform ID: ${contEval.transform_id}`);
        
        // Get the LLM eval details
        const llmEvalKey = `${contEval.llm_eval_name}:${contEval.llm_eval_version}`;
        if (!llmEvalsMap[llmEvalKey]) {
          try {
            const llmEvalResponse = await apiClient.get(
              `/api/v1/tasks/${taskId}/llm_evals/${encodeURIComponent(contEval.llm_eval_name)}/versions/${contEval.llm_eval_version}`
            );
            llmEvalsMap[llmEvalKey] = llmEvalResponse.data;
            console.log(`      ✓ Fetched LLM eval details`);
          } catch (error: any) {
            console.error(`      ✗ Error fetching LLM eval:`, error.message);
          }
        }
        
        // Get the transform details
        if (contEval.transform_id && !transformsMap[contEval.transform_id]) {
          try {
            const transformResponse = await apiClient.get(
              `/api/v1/traces/transforms/${contEval.transform_id}`
            );
            transformsMap[contEval.transform_id] = transformResponse.data;
            console.log(`      ✓ Fetched transform: ${transformResponse.data.name}`);
          } catch (error: any) {
            console.error(`      ✗ Error fetching transform:`, error.message);
          }
        }
        
        // Store the continuous eval with all its data
        continuousEvals.push({
          id: contEval.id,
          name: contEval.name,
          description: contEval.description,
          llm_eval_name: contEval.llm_eval_name,
          llm_eval_version: contEval.llm_eval_version,
          transform_id: contEval.transform_id,
          created_at: contEval.created_at,
          updated_at: contEval.updated_at,
        });
        
        console.log(`      ✓ Continuous eval processed`);
      }
    } else {
      console.log(`   ⚠️  No continuous evals found for this task`);
    }
  } catch (error: any) {
    console.error("   ✗ Error extracting continuous evals:", error.message || error);
  }
  
  // Save continuous evals
  await fs.writeFile(
    path.join(BOOTSTRAP_DIR, "continuous-evals.json"),
    JSON.stringify(continuousEvals, null, 2)
  );
  console.log(`   ✓ Saved ${continuousEvals.length} continuous evals to: continuous-evals.json\n`);
  
  // 4. Save LLM Evals
  console.log("4. Saving LLM evals...");
  const llmEvalsArray = Object.values(llmEvalsMap);
  const llmEvalsObj: any = {};
  
  for (const llmEval: any of llmEvalsArray) {
    llmEvalsObj[llmEval.name] = {
      name: llmEval.name,
      instructions: llmEval.instructions,
      model_name: llmEval.model_name,
      model_provider: llmEval.model_provider,
      version: llmEval.version,
      tags: llmEval.tags || [],
      config: llmEval.config || {},
      variables: llmEval.variables || [],
    };
  }
  
  await fs.writeFile(
    path.join(BOOTSTRAP_DIR, "llm-evals.json"),
    JSON.stringify(llmEvalsObj, null, 2)
  );
  console.log(`   ✓ Saved ${llmEvalsArray.length} LLM evals to: llm-evals.json\n`);
  
  // 5. Save Transforms
  console.log("5. Saving transforms...");
  const transformsArray = Object.values(transformsMap);
  
  await fs.writeFile(
    path.join(BOOTSTRAP_DIR, "transforms.json"),
    JSON.stringify(transformsMap, null, 2)
  );
  console.log(`   ✓ Saved ${transformsArray.length} transforms to: transforms.json\n`);

  // 6. Extract Datasets
  console.log("6. Extracting datasets...");
  const datasets: any[] = [];
  
  try {
    // Get all datasets for the task
    const datasetsResponse = await apiClient.get(
      `/api/v2/tasks/${taskId}/datasets/search`
    );
    
    const datasetsData = datasetsResponse.data.datasets || [];
    
    if (datasetsData.length > 0) {
      console.log(`   Found ${datasetsData.length} dataset(s)`);
      
      for (const dataset of datasetsData) {
        console.log(`   Processing: ${dataset.name}...`);
        console.log(`      ID: ${dataset.id}`);
        console.log(`      Latest Version: ${dataset.latest_version_number}`);
        
        // Get the latest version with all rows
        try {
          const versionResponse = await apiClient.get(
            `/api/v2/datasets/${dataset.id}/versions/${dataset.latest_version_number}`
          );
          
          const versionData = versionResponse.data;
          
          console.log(`      ✓ Fetched version ${versionData.version_number}`);
          console.log(`      Columns: ${versionData.column_names?.length || 0}`);
          console.log(`      Rows: ${versionData.rows?.length || 0}`);
          
          datasets.push({
            name: dataset.name,
            description: dataset.description,
            metadata: dataset.metadata,
            version: {
              version_number: versionData.version_number,
              column_names: versionData.column_names,
              rows: versionData.rows,
            },
          });
          
          console.log(`      ✓ Dataset processed`);
        } catch (error: any) {
          console.error(`      ✗ Error fetching version:`, error.message);
        }
      }
    } else {
      console.log(`   ⚠️  No datasets found for this task`);
    }
  } catch (error: any) {
    console.error("   ✗ Error extracting datasets:", error.message || error);
  }
  
  await fs.writeFile(
    path.join(BOOTSTRAP_DIR, "datasets.json"),
    JSON.stringify(datasets, null, 2)
  );
  console.log(`   ✓ Saved ${datasets.length} datasets to: datasets.json\n`);

  // 7. Copy test questions
  console.log("7. Copying test questions...");
  try {
    const questionsPath = path.join(__dirname, "test-questions.json");
    const questionsData = await fs.readFile(questionsPath, "utf-8");
    
    await fs.writeFile(
      path.join(BOOTSTRAP_DIR, "test-questions.json"),
      questionsData
    );
    
    const questions = JSON.parse(questionsData);
    console.log(`   ✓ Copied ${questions.questions.length} test questions\n`);
  } catch (error) {
    console.error("   ✗ Error copying test questions:", error);
    console.log("");
  }

  // Print summary
  console.log("========================================");
  console.log("Bootstrap extraction complete!");
  console.log("========================================\n");
  
  console.log("Extracted:");
  console.log(`  ✓ Task configuration`);
  console.log(`  ✓ ${Object.keys(prompts).length} prompts`);
  console.log(`  ✓ ${llmEvalsArray.length} LLM evals`);
  console.log(`  ✓ ${continuousEvals.length} continuous evals (with transforms)`);
  console.log(`  ✓ ${transformsArray.length} transforms`);
  console.log(`  ✓ ${datasets.length} datasets`);
  console.log(`  ✓ Test questions`);
  console.log("");
  console.log(`All data saved to: ${BOOTSTRAP_DIR}`);
  console.log("========================================");
}

// Run the extraction
main().catch((error) => {
  console.error("Fatal error in bootstrap extraction:", error);
  process.exit(1);
});

