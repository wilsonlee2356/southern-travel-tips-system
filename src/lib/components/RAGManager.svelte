<script>
    import { onMount } from 'svelte';
    import { fetchRAGModels, deleteRAGModel } from '$lib/utils/adapterApi.js';

    // State
    let ragModels = [];
    let isLoading = false;
    let error = '';
    let success = '';

    // Load data on mount
    onMount(async () => {
        await loadData();
    });

    async function loadData() {
        isLoading = true;
        error = '';
        
        try {
            console.log('Loading fine-tuned models...');
            // Load RAG models (which are the fine-tuned models ready to use)
            const ragResult = await fetchRAGModels();
            console.log('Fine-tuned models result:', ragResult);
            
            if (ragResult.success) {
                ragModels = ragResult.rag_models;
                console.log('Loaded fine-tuned models:', ragModels);
            } else {
                console.error('Failed to load fine-tuned models:', ragResult.error);
                error = `Failed to load fine-tuned models: ${ragResult.error || 'Unknown error'}`;
            }
            
        } catch (err) {
            console.error('Error loading data:', err);
            error = `Error loading data: ${err.message}`;
        } finally {
            isLoading = false;
        }
    }

    async function deleteModel(modelName) {
        if (!confirm(`Are you sure you want to delete the fine-tuned model "${modelName}"?\n\nThis will delete:\n• The fine-tuned model\n• The adapter export files\n• The Ollama model registration\n\nThis action cannot be undone.`)) {
            return;
        }
        
        isLoading = true;
        error = '';
        success = '';
        
        try {
            const result = await deleteRAGModel(modelName);
            console.log('Delete result:', result);
            
            if (result.success) {
                success = `Fine-tuned model "${modelName}" and its adapter export deleted successfully`;
                await loadData(); // Refresh the list
            } else {
                error = result.error || 'Failed to delete model';
            }
        } catch (err) {
            console.error('Error deleting model:', err);
            error = `Error deleting model: ${err.message}`;
        } finally {
            isLoading = false;
        }
    }

    function clearMessages() {
        error = '';
        success = '';
    }
</script>

<div class="fine-tuned-models-manager">
    <div class="header-section">
        <div class="title-container">
            <h2>Fine-tuned Models Manager</h2>
            <p class="description">Manage your fine-tuned models that are ready to use in Flight Search. These models are automatically created after fine-tuning completes.</p>
        </div>
        <button on:click={loadData} class="btn btn-secondary" disabled={isLoading}>
            {isLoading ? 'Loading...' : 'Refresh Models'}
        </button>
    </div>
    
    <!-- Info Section -->
    <div class="info-section">
        <h3>📋 About Fine-tuned Models</h3>
        <div class="info-content">
            <p>These are your fine-tuned models that are ready to use in the Flight Search page. Each model combines a trained adapter with the base model using lightweight merging.</p>
            <ul>
                <li><strong>Created automatically</strong> after fine-tuning completes</li>
                <li><strong>Ready to use</strong> in Flight Search page immediately</li>
                <li><strong>Optimized for RAG</strong> with travel content generation</li>
                <li><strong>Lightweight</strong> - uses existing base model with adapter</li>
            </ul>
        </div>
    </div>

    <!-- Fine-tuned Models List -->
    <div class="models-section">
        <h3>Available Fine-tuned Models</h3>
        {#if ragModels.length === 0}
            <div class="no-models">
                <p>📭 No fine-tuned models found.</p>
                <p>Fine-tune a model first, and it will automatically appear here after training completes.</p>
            </div>
        {:else}
            <div class="models-list">
                {#each ragModels as model}
                    <div class="model-card">
                        <div class="model-header">
                            <h4>🤖 {model.rag_model_name}</h4>
                        </div>
                        
                        <div class="model-details">
                            <div class="detail-row">
                                <span class="label">Adapter:</span>
                                <span class="value">{model.adapter_name}</span>
                            </div>
                            <div class="detail-row">
                                <span class="label">Base Model:</span>
                                <span class="value">{model.base_model}</span>
                            </div>
                            <div class="detail-row">
                                <span class="label">Created:</span>
                                <span class="value">{new Date(model.created_at).toLocaleString()}</span>
                            </div>
                            <!-- <div class="detail-row">
                                <span class="label">Purpose:</span>
                                <span class="value">{model.purpose}</span>
                            </div> -->
                        </div>
                        
                        <div class="model-actions">
                            <button 
                                on:click={() => deleteModel(model.rag_model_name)} 
                                class="btn btn-danger"
                                disabled={isLoading}
                            >
                                🗑️ Delete Model
                            </button>
                        </div>
                        
                    </div>
                {/each}
            </div>
        {/if}
    </div>

    <!-- Messages -->
    {#if error}
        <div class="alert alert-error">
            <strong>❌ Error:</strong> {error}
            <button on:click={clearMessages} class="close-btn">×</button>
        </div>
    {/if}

    {#if success}
        <div class="alert alert-success">
            <strong>✅ Success:</strong> {success}
            <button on:click={clearMessages} class="close-btn">×</button>
        </div>
    {/if}

    {#if isLoading}
        <div class="loading">
            <p>⏳ Loading...</p>
        </div>
    {/if}
</div>

<style>
    .fine-tuned-models-manager {
        max-width: 900px;
        margin: 0 auto;
        padding: 20px;
    }

    .header-section {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 30px;
        padding: 20px;
        background: #ffffff;
        border-radius: 12px;
        color: black;
    }

    .header-section h2 {
        margin: 0 0 8px 0;
        font-size: 1.8rem;
        font-weight: 600;
    }

    .title-container {
        flex: 1;
    }

    .description {
        margin: 0;
        font-size: 0.9rem;
        opacity: 0.9;
        line-height: 1.4;
    }

    .info-section, .models-section {
        margin-bottom: 30px;
        padding: 25px;
        border: 1px solid #d1d5db;
        border-radius: 12px;
        background: #ffffff;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }

    .info-section h3 {
        margin-top: 0;
        color: #495057;
        font-size: 1.3rem;
    }

    .info-content {
        color: #6c757d;
    }

    .info-content ul {
        margin: 15px 0;
        padding-left: 20px;
    }

    .info-content li {
        margin: 8px 0;
    }

    .models-section h3 {
        margin-top: 0;
        color: #495057;
        font-size: 1.3rem;
    }

    .no-models {
        text-align: center;
        padding: 40px 20px;
        color: #6c757d;
        background: white;
        border-radius: 8px;
        border: 2px dashed #dee2e6;
    }

    .no-models p {
        margin: 10px 0;
        font-size: 1.1rem;
    }

    .models-list {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
        gap: 20px;
    }

    .model-card {
        padding: 20px;
        border: 1px solid #dee2e6;
        border-radius: 12px;
        background: white;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }

    .model-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 16px rgba(0,0,0,0.15);
    }

    .model-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 15px;
        padding-bottom: 10px;
        border-bottom: 1px solid #e9ecef;
    }

    .model-header h4 {
        margin: 0;
        color: #495057;
        font-size: 1.1rem;
        font-weight: 600;
    }

    .status-badge {
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 500;
        text-transform: uppercase;
    }

    .status-ready {
        background: #d4edda;
        color: #155724;
    }


    .model-details {
        margin-bottom: 15px;
    }

    .detail-row {
        display: flex;
        justify-content: space-between;
        margin: 8px 0;
        padding: 4px 0;
    }

    .detail-row .label {
        font-weight: 600;
        color: #6c757d;
        font-size: 0.9rem;
    }

    .detail-row .value {
        color: #495057;
        font-size: 0.9rem;
        text-align: right;
        max-width: 60%;
        word-break: break-word;
    }

    .model-actions {
        margin: 15px 0;
        padding-top: 15px;
        border-top: 1px solid #e9ecef;
    }

    .usage-info {
        background: #e7f3ff;
        padding: 12px;
        border-radius: 6px;
        border-left: 4px solid #007bff;
    }

    .usage-info p {
        margin: 0;
        font-size: 0.9rem;
        color: #004085;
    }

    .btn {
        padding: 10px 20px;
        border: none;
        border-radius: 6px;
        cursor: pointer;
        font-weight: 500;
        transition: all 0.2s ease;
    }

    .btn-secondary {
        background: #6c757d;
        color: white;
    }

    .btn-secondary:hover:not(:disabled) {
        background: #5a6268;
    }

    .btn-danger {
        background: #dc3545;
        color: white;
    }

    .btn-danger:hover:not(:disabled) {
        background: #c82333;
    }

    .btn:disabled {
        opacity: 0.6;
        cursor: not-allowed;
    }

    .alert {
        padding: 15px 20px;
        margin: 20px 0;
        border-radius: 8px;
        position: relative;
        font-weight: 500;
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
        top: 8px;
        right: 12px;
        background: none;
        border: none;
        font-size: 18px;
        cursor: pointer;
        color: inherit;
        opacity: 0.7;
    }

    .close-btn:hover {
        opacity: 1;
    }

    .loading {
        text-align: center;
        padding: 40px;
        color: #6c757d;
        font-size: 1.1rem;
    }

    /* Dark mode support */
    @media (prefers-color-scheme: dark) {
        .fine-tuned-models-manager {
            background: #1a1a1a;
            color: #e9ecef;
        }

        .info-section, .models-section {
            background: #ffffff;
            border-color: #d1d5db;
            color: #000000;
        }

        .model-card {
            background: #2d3748;
            border-color: #4a5568;
        }

        .no-models {
            background: #2d3748;
            border-color: #4a5568;
            color: #a0aec0;
        }

        .usage-info {
            background: #2b6cb0;
            border-left-color: #3182ce;
        }

        .usage-info p {
            color: #bee3f8;
        }
    }
</style>