# Weaviate Retrievals Playground

A comprehensive playground for experimenting with Weaviate vector database retrievals. This playground allows users to connect to their Weaviate instances, explore collections, and test different search methods and configurations.

## Features

### 🔌 Connection Management

- Connect to Weaviate instances using URL and API key
- Secure connection validation
- Easy disconnect functionality

### 📊 Collection Explorer

- View all available collections in your Weaviate instance
- See collection metadata including:
  - Total number of objects
  - Number of properties
  - Vectorizer information
- Select collections for querying

### 🔍 Query Interface

- **Near Text Search**: Semantic vector search using text similarity
- **BM25 Search**: Traditional keyword-based search
- **Hybrid Search**: Combines vector and keyword search for optimal results
- Real-time query execution with loading states

### ⚙️ Advanced Settings

- **Result Limit**: Control number of returned results (1-100)
- **Distance Threshold**: Adjust vector similarity threshold for vector searches
- **Hybrid Alpha**: Balance between vector and keyword search (0-1)
- **Include Options**: Choose to include metadata and vector embeddings in results

### 📋 Results Display

- Expandable result cards with detailed information
- Property inspection with JSON formatting
- Metadata display including:
  - Distance/similarity scores
  - BM25 scores
  - Explain scores for debugging
- Vector embedding visualization (when included)
- Color-coded scoring for easy interpretation

## Usage

1. **Connect**: Enter your Weaviate URL and API key to establish a connection
2. **Select Collection**: Choose a collection from the list to query against
3. **Configure Settings**: Adjust search parameters based on your needs
4. **Query**: Enter your search text and select a search method
5. **Explore Results**: Click on results to expand and examine detailed information

## Search Methods

### Near Text (Vector Search)

- Uses semantic similarity to find documents with similar meaning
- Best for: Finding conceptually related content
- Distance threshold controls similarity requirements

### BM25 (Keyword Search)

- Traditional keyword-based search using BM25 algorithm
- Best for: Exact keyword matches and traditional search
- Higher scores indicate better keyword matches

### Hybrid Search

- Combines vector and keyword search for comprehensive results
- Alpha parameter controls the balance:
  - 0.0 = Pure vector search
  - 1.0 = Pure keyword search
  - 0.5 = Balanced approach (default)

## Technical Details

- Built with React and TypeScript
- Uses HTTP-based Weaviate client (browser-compatible)
- Responsive design with Tailwind CSS
- All state managed in browser memory (no backend required)
- Error handling and loading states throughout
- Configured to work in browser environments (no Node.js dependencies)

## Components

- `ConnectionForm`: Handles Weaviate connection setup
- `CollectionSelector`: Displays and manages collection selection
- `QueryInterface`: Provides query input and search method selection
- `SettingsPanel`: Manages search configuration options
- `ResultsDisplay`: Shows search results with detailed inspection
- `WeaviateService`: Core service for Weaviate operations

## Future Enhancements

- Backend integration for persistent settings
- Query history and saved searches
- Advanced filtering options
- Batch query capabilities
- Export functionality for results
