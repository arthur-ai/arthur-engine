# Image Analysis Agent

This is a starter template for building multimodal AI agents that incorporate trace monitoring using Arthur's GenAI Engine.

## Prerequisites

- Node.js 18+
- Yarn package manager

## Getting Started

1. **Set up environment variables**

   Create a `.env` file in this directory and add the following environment variables:

   ```bash
   # Copy the example file
   cp .env.example .env
   ```

   Then edit the `.env` file with your actual values:

   ```bash
   # OpenAI API Configuration
   OPENAI_API_KEY=your-openai-api-key-here

   # Arthur Engine Configuration
   ARTHUR_BASE_URL=https://your-arthur-instance.com
   ARTHUR_API_KEY=your-arthur-api-key-here
   ARTHUR_TASK_ID=your-arthur-task-id-here
   ```

2. **Install dependencies**

   ```bash
   yarn install
   ```

3. **Start the development server**

   ```bash
   yarn dev
   ```

## Contributing

Feel free to submit issues and enhancement requests!

## License

This project is licensed under the MIT License - see the LICENSE file for details.
