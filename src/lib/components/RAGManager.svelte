<script>
    import { onMount } from 'svelte';
    import { createRAGModel, fetchRAGModels, getCurrentRAGConfig, testRAGModel, fetchAdapters, deleteRAGModel } from '$lib/utils/adapterApi.js';

    // State
    let adapters = [];
    let ragModels = [];
    let currentConfig = null;
    let selectedAdapter = '';
    let selectedBaseModel = 'qwen2.5:14b';
    let isLoading = false;
    let error = '';
    let success = '';
    let testResult = null;
    let testQuery = '測試RAG功能';

    // Load data on mount
    onMount(async () => {
        await loadData();
    });

    async function loadData() {
        isLoading = true;
        error = '';
        
        try {
            console.log('Loading adapters...');
            // Load adapters
            const adaptersResult = await fetchAdapters();
            console.log('Adapters result:', adaptersResult);
            if (adaptersResult.success) {
                adapters = adaptersResult.adapters;
            } else {
                console.error('Failed to load adapters:', adaptersResult.error);
                error = `Failed to load adapters: ${adaptersResult.error}`;
            }

            console.log('Loading RAG models...');
            // Load RAG models
            const ragResult = await fetchRAGModels();
            console.log('RAG models result:', ragResult);
            if (ragResult.success) {
                ragModels = ragResult.rag_models;
            } else {
                console.error('Failed to load RAG models:', ragResult.error || 'Unknown error');
                error = `Failed to load RAG models: ${ragResult.error || 'Unknown error'}`;
            }

            console.log('Loading current config...');
            // Load current config
            const configResult = await getCurrentRAGConfig();
            console.log('Config result:', configResult);
            if (configResult.success) {
                currentConfig = configResult.config;
            } else {
                console.error('Failed to load config:', configResult.error);
            }
        } catch (err) {
            console.error('Error in loadData:', err);
            error = `Failed to load data: ${err.message}`;
        } finally {
            isLoading = false;
        }
    }

    async function createRAG() {
        if (!selectedAdapter || selectedAdapter === 'undefined') {
            error = 'Please select a valid adapter';
            return;
        }

        isLoading = true;
        error = '';
        success = '';

        try {
            console.log('Creating RAG model with adapter:', selectedAdapter, 'base model:', selectedBaseModel);
            // Find the adapter export ID for the selected adapter
            const selectedAdapterData = adapters.find(adapter => 
                (adapter.adapter_name || adapter.adapter_id || adapter.id || adapter.name) === selectedAdapter
            );
            
            if (!selectedAdapterData) {
                error = 'Selected adapter not found';
                return;
            }
            
            const adapterId = selectedAdapterData.export_id || selectedAdapterData.adapter_name;
            console.log('Using adapter ID:', adapterId);
            
            const result = await createRAGModel(adapterId, selectedBaseModel);
            console.log('RAG model creation result:', result);
            success = `RAG model created successfully: ${result.model_name}`;
            await loadData(); // Refresh the list
        } catch (err) {
            console.error('Error creating RAG model:', err);
            error = `Failed to create RAG model: ${err.message}`;
        } finally {
            isLoading = false;
        }
    }

    async function testModel(modelName) {
        try {
            const result = await testRAGModel(modelName, testQuery);
            testResult = result;
        } catch (err) {
            error = `Failed to test model: ${err.message}`;
        }
    }

    async function deleteModel(modelName) {
        if (!confirm(`Are you sure you want to delete RAG model "${modelName}"? This action cannot be undone.`)) {
            return;
        }
        
        try {
            isLoading = true;
            const result = await deleteRAGModel(modelName);
            
            if (result.success) {
                success = `RAG model "${modelName}" deleted successfully`;
                await loadData(); // Refresh the list
            } else {
                error = `Failed to delete RAG model: ${result.error}`;
            }
        } catch (err) {
            console.error('Error deleting RAG model:', err);
            error = `Failed to delete RAG model: ${err.message}`;
        } finally {
            isLoading = false;
        }
    }

    function clearMessages() {
        error = '';
        success = '';
        testResult = null;
    }
</script>

<div class="rag-manager">
    <div class="header-section">
        <h2>RAG Model Management</h2>
        <button on:click={loadData} class="btn btn-secondary" disabled={isLoading}>
            {isLoading ? 'Loading...' : 'Refresh Data'}
        </button>
    </div>
    
    <!-- Current RAG Configuration -->
    {#if currentConfig}
        <div class="config-section">
            <h3>Current RAG Configuration</h3>
            <div class="config-info">
                <p><strong>Embedding Engine:</strong> {currentConfig.embedding_engine}</p>
                <p><strong>Embedding Model:</strong> {currentConfig.embedding_model}</p>
                <p><strong>Ollama Base URL:</strong> {currentConfig.ollama_base_url}</p>
                <p><strong>Chunk Size:</strong> {currentConfig.chunk_size}</p>
                <p><strong>Top K:</strong> {currentConfig.top_k}</p>
            </div>
        </div>
    {/if}

    <!-- Create RAG Model -->
    <div class="create-section">
        <h3>Create RAG Model</h3>
        <div class="form-group">
            <label for="adapter-select">Select Adapter:</label>
            <select id="adapter-select" bind:value={selectedAdapter}>
                <option value="">Choose an adapter...</option>
                {#each adapters as adapter}
                    <option value={adapter.adapter_name || adapter.adapter_id || adapter.id || adapter.name}>
                        {adapter.adapter_name || adapter.adapter_id || adapter.id || adapter.name || 'Unknown Adapter'}
                    </option>
                {/each}
            </select>
            {#if adapters.length === 0}
                <p class="text-sm text-gray-500">No adapters found. Make sure your backend is running on port 8001.</p>
            {/if}
        </div>
        
        <div class="form-group">
            <label for="base-model">Base Model:</label>
            <input 
                id="base-model" 
                type="text" 
                bind:value={selectedBaseModel} 
                placeholder="qwen2.5:14b"
            />
        </div>
        
        <button 
            on:click={createRAG} 
            disabled={isLoading || !selectedAdapter}
            class="btn btn-primary"
        >
            {isLoading ? 'Creating...' : 'Create RAG Model'}
        </button>
    </div>

    <!-- RAG Models List -->
    <div class="models-section">
        <h3>Available RAG Models</h3>
        {#if ragModels.length === 0}
            <p>No RAG models found. Create one above.</p>
        {:else}
            <div class="models-list">
                {#each ragModels as model}
                    <div class="model-card">
                        <h4>{model.rag_model_name}</h4>
                        <p><strong>Adapter:</strong> {model.adapter_name}</p>
                        <p><strong>Base Model:</strong> {model.base_model}</p>
                        <p><strong>Created:</strong> {new Date(model.created_at).toLocaleString()}</p>
                        <p><strong>Status:</strong> {model.status}</p>
                        
                        <div class="model-actions">
                            <button 
                                on:click={() => testModel(model.rag_model_name)} 
                                class="btn btn-secondary"
                            >
                                Test Model
                            </button>
                            <button 
                                on:click={() => deleteModel(model.rag_model_name)} 
                                class="btn btn-danger"
                                disabled={isLoading}
                            >
                                Delete Model
                            </button>
                        </div>
                    </div>
                {/each}
            </div>
        {/if}
    </div>

    <!-- Test Section -->
    {#if testResult}
        <div class="test-section">
            <h3>Test Results</h3>
            <div class="test-query">
                <label for="test-query">Test Query:</label>
                <input 
                    id="test-query" 
                    type="text" 
                    bind:value={testQuery} 
                    placeholder="測試RAG功能"
                />
            </div>
            
            {#if testResult.success}
                <div class="test-success">
                    <h4>✅ Test Successful</h4>
                    <p><strong>Model:</strong> {testResult.model}</p>
                    <p><strong>Query:</strong> {testResult.test_query}</p>
                    <div class="response">
                        <strong>Response:</strong>
                        <pre>{testResult.response}</pre>
                    </div>
                </div>
            {:else}
                <div class="test-error">
                    <h4>❌ Test Failed</h4>
                    <p><strong>Error:</strong> {testResult.error}</p>
                </div>
            {/if}
        </div>
    {/if}

    <!-- Messages -->
    {#if error}
        <div class="alert alert-error">
            <strong>Error:</strong> {error}
            <button on:click={clearMessages} class="close-btn">×</button>
        </div>
    {/if}

    {#if success}
        <div class="alert alert-success">
            <strong>Success:</strong> {success}
            <button on:click={clearMessages} class="close-btn">×</button>
        </div>
    {/if}

    {#if isLoading}
        <div class="loading">
            <p>Loading...</p>
        </div>
    {/if}
</div>

<style>
    .rag-manager {
        max-width: 800px;
        margin: 0 auto;
        padding: 20px;
    }

    .config-section, .create-section, .models-section, .test-section {
        margin-bottom: 30px;
        padding: 20px;
        border: 1px solid #ddd;
        border-radius: 8px;
        background: #f9f9f9;
    }

    .form-group {
        margin-bottom: 15px;
    }

    .form-group label {
        display: block;
        margin-bottom: 5px;
        font-weight: bold;
    }

    .form-group select,
    .form-group input {
        width: 100%;
        padding: 8px;
        border: 1px solid #ccc;
        border-radius: 4px;
    }

    .btn {
        padding: 10px 20px;
        border: none;
        border-radius: 4px;
        cursor: pointer;
        margin-right: 10px;
    }

    .btn-primary {
        background: #007bff;
        color: white;
    }

    .btn-secondary {
        background: #6c757d;
        color: white;
    }

    .btn-danger {
        background: #dc3545;
        color: white;
    }

    .btn:disabled {
        opacity: 0.6;
        cursor: not-allowed;
    }

    .models-list {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
        gap: 20px;
    }

    .model-card {
        padding: 15px;
        border: 1px solid #ddd;
        border-radius: 8px;
        background: white;
    }

    .model-actions {
        margin-top: 10px;
    }

    .test-section {
        background: #f0f8ff;
    }

    .test-success {
        background: #d4edda;
        padding: 15px;
        border-radius: 4px;
        margin-top: 10px;
    }

    .test-error {
        background: #f8d7da;
        padding: 15px;
        border-radius: 4px;
        margin-top: 10px;
    }

    .response pre {
        background: #f8f9fa;
        padding: 10px;
        border-radius: 4px;
        overflow-x: auto;
        white-space: pre-wrap;
    }

    .alert {
        padding: 15px;
        margin: 15px 0;
        border-radius: 4px;
        position: relative;
    }

    .alert-error {
        background: #f8d7da;
        color: #721c24;
        border: 1px solid #f5c6cb;
    }

    .alert-success {
        background: #d4edda;
        color: #155724;
        border: 1px solid #c3e6cb;
    }

    .close-btn {
        position: absolute;
        top: 5px;
        right: 10px;
        background: none;
        border: none;
        font-size: 20px;
        cursor: pointer;
    }

    .loading {
        text-align: center;
        padding: 20px;
    }

    .config-info p {
        margin: 5px 0;
    }

    .header-section {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 20px;
        padding: 15px;
        background: #f8f9fa;
        border-radius: 8px;
    }

    .header-section h2 {
        margin: 0;
    }
</style>
