<script>
    import { onMount } from 'svelte';
    import { fetchRAGModels, deleteRAGModel } from '$lib/utils/adapterApi.js';
    
    // Add new API functions for fine-tuned models
    async function fetchFineTunedModels() {
        try {
            console.log('🔍 Searching for fine-tuned models...');
            
            // First, get all adapter exports from the backend
            const adapterResponse = await fetch('http://localhost:8001/api/adapters/list');
            if (!adapterResponse.ok) {
                console.warn('Could not fetch adapter exports, trying Ollama models only');
                return await fetchFromOllamaOnly();
            }
            
            const adapterData = await adapterResponse.json();
            const adapters = adapterData.adapters || [];
            console.log('📁 Found adapter exports:', adapters);
            
            // Get all Ollama models
            const ollamaResponse = await fetch(`http://127.0.0.1:11434/api/tags`);
            if (!ollamaResponse.ok) throw new Error('Failed to fetch Ollama models');
            
            const ollamaData = await ollamaResponse.json();
            const ollamaModels = ollamaData.models || [];
            console.log('🤖 Ollama API Response Status:', ollamaResponse.status);
            console.log('🤖 Ollama API Response Data:', ollamaData);
            console.log('🤖 Found Ollama models:', ollamaModels.map(m => m.name));
            
            // Also get RAG models for additional info
            const ragResult = await fetchRAGModels();
            const ragModels = ragResult.success ? ragResult.rag_models : [];
            
            // For each adapter export, try to find corresponding Ollama model
            const enrichedModels = [];
            
            for (const adapter of adapters) {
                const exportId = adapter.export_id;
                console.log(`🔍 Looking for Ollama model for export_id: ${exportId}`);
                
                // Extract the actual training ID from the export_id
                // export_id format: "adapter_export_training_1759317710"
                // We need to extract: "training_1759317710"
                let trainingId = exportId;
                if (exportId.startsWith('adapter_export_')) {
                    trainingId = exportId.replace('adapter_export_', '');
                }
                console.log(`🔍 Extracted training ID: ${trainingId}`);
                
                // Look for corresponding Ollama models
                const possibleOllamaNames = [
                    `${trainingId}:latest`,  // Most common pattern: training_1759317710:latest
                    trainingId,              // Without :latest: training_1759317710
                    `${trainingId}_ollama`,  // Legacy pattern: training_1759317710_ollama
                    `${trainingId}_rag_ollama`, // Legacy RAG pattern
                    `${trainingId}_ollama:latest`, // Legacy pattern with :latest
                    `${trainingId}_rag_ollama:latest` // Legacy RAG pattern with :latest
                ];
                
                console.log(`🔍 Searching for these possible names:`, possibleOllamaNames);
                console.log(`🔍 Available Ollama models:`, ollamaModels.map(m => m.name));
                
                const ollamaModel = ollamaModels.find(model => 
                    possibleOllamaNames.includes(model.name)
                );
                
                if (ollamaModel) {
                    console.log(`✅ Found Ollama model: ${ollamaModel.name} for adapter: ${exportId}`);
                    
                    // Find corresponding RAG model info
                    const ragModel = ragModels.find(rm => 
                        rm.ollama_model_name === ollamaModel.name || 
                        rm.export_id === exportId
                    );
                    
                    enrichedModels.push({
                        name: ollamaModel.name,
                        size: ollamaModel.size,
                        modified_at: ollamaModel.modified_at,
                        digest: ollamaModel.digest,
                        is_rag_model: !!ragModel,
                        rag_info: ragModel,
                        export_id: exportId,
                        adapter_info: adapter,
                        model_type: ollamaModel.name.includes('_rag_') ? 'RAG Model' : 'Simple Merged Model',
                        has_ollama_model: true
                    });
                } else {
                    console.log(`⚠️ No Ollama model found for adapter export: ${exportId}`);
                    // Skip this adapter export if no corresponding Ollama model exists
                }
            }
            
            console.log(`📊 Final enriched models: ${enrichedModels.length}`);
            
            return {
                success: true,
                models: enrichedModels,
                count: enrichedModels.length
            };
            
        } catch (error) {
            console.error('Error fetching fine-tuned models:', error);
            return {
                success: false,
                models: [],
                count: 0,
                error: error.message
            };
        }
    }
    
    // Fallback function to search Ollama models only
    async function fetchFromOllamaOnly() {
        try {
            console.log('🔄 Fallback: Searching Ollama models only...');
            
            const response = await fetch(`http://127.0.0.1:11434/api/tags`);
            if (!response.ok) throw new Error('Failed to fetch Ollama models');
            
            const data = await response.json();
            const ollamaModels = data.models || [];
            
            // Filter for fine-tuned models (those created from our fine-tuning process)
            const fineTunedModels = ollamaModels.filter(model => {
                const name = model.name.toLowerCase();
                // Only show merged models created from our fine-tuning process
                // Pattern: training_{timestamp} or training_{timestamp}_ollama or training_{timestamp}_rag_ollama
                // Support both with and without :latest suffix
                return (name.includes('training_') && name.includes('_')) || 
                       (name.includes('_ollama') && name.includes('training_'));
            });
            
            console.log(`🔍 Found ${fineTunedModels.length} fine-tuned models in Ollama:`, fineTunedModels.map(m => m.name));
            
            // Also get RAG models for additional info
            const ragResult = await fetchRAGModels();
            const ragModels = ragResult.success ? ragResult.rag_models : [];
            
            // Combine and enrich the data
            const enrichedModels = fineTunedModels.map(model => {
                const ragModel = ragModels.find(rm => 
                    rm.ollama_model_name === model.name || 
                    model.name.includes(rm.export_id)
                );
                
                return {
                    name: model.name,
                    size: model.size,
                    modified_at: model.modified_at,
                    digest: model.digest,
                    is_rag_model: !!ragModel,
                    rag_info: ragModel,
                    export_id: model.name.includes('_ollama') ? model.name.split('_ollama')[0] : model.name.split(':')[0], // Extract training ID
                    model_type: model.name.includes('_rag_') ? 'RAG Model' : 'Simple Merged Model',
                    has_ollama_model: true
                };
            });
            
            return {
                success: true,
                models: enrichedModels,
                count: enrichedModels.length
            };
        } catch (error) {
            console.error('Error in fallback fetch:', error);
            return {
                success: false,
                models: [],
                count: 0,
                error: error.message
            };
        }
    }
    
    async function deleteFineTunedModel(modelName) {
        try {
            const response = await fetch(`http://localhost:8001/api/fine-tuned-models/${encodeURIComponent(modelName)}/delete`, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to delete model');
            }
            
            return await response.json();
        } catch (error) {
            console.error('Error deleting fine-tuned model:', error);
            return {
                success: false,
                error: error.message
            };
        }
    }

    // State
    let fineTunedModels = [];
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
            // Load all fine-tuned models (both simple merged and RAG models)
            const result = await fetchFineTunedModels();
            console.log('Fine-tuned models result:', result);
            
            if (result.success) {
                fineTunedModels = result.models;
                console.log('Loaded fine-tuned models:', fineTunedModels);
            } else {
                console.error('Failed to load fine-tuned models:', result.error);
                error = `Failed to load fine-tuned models: ${result.error || 'Unknown error'}`;
            }
            
        } catch (err) {
            console.error('Error loading data:', err);
            error = `Error loading data: ${err.message}`;
        } finally {
            isLoading = false;
        }
    }

    async function deleteModel(modelName) {
        if (!confirm(`Are you sure you want to delete the fine-tuned model "${modelName}"?\n\nThis will delete:\n• The Ollama model\n• The adapter export files\n• All associated training data\n\nThis action cannot be undone.`)) {
            return;
        }
        
        isLoading = true;
        error = '';
        success = '';
        
        try {
            const result = await deleteFineTunedModel(modelName);
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
            <h2>Merged Models Manager</h2>
            <p class="description">Manage your merged models created from fine-tuning. These are complete models ready to use in Flight Search, created by combining base models with trained adapters.</p>
        </div>
        <button on:click={loadData} class="btn btn-secondary" disabled={isLoading}>
            {isLoading ? 'Loading...' : 'Refresh Models'}
        </button>
    </div>
    
    <!-- Info Section -->
    <div class="info-section">
        <h3>📋 About Merged Models</h3>
        <div class="info-content">
            <p>These are your merged models created from fine-tuning sessions. Each model combines a trained adapter with the base model to create a complete, ready-to-use model.</p>
            <ul>
                <li><strong>Created automatically</strong> after fine-tuning completes</li>
                <li><strong>Complete models</strong> - full merge of base model + adapter</li>
                <li><strong>Ready to use</strong> in Flight Search page immediately</li>
                <li><strong>Optimized for content generation</strong> with your training data</li>
            </ul>
        </div>
    </div>

    <!-- Merged Models List -->
    <div class="models-section">
        <h3>Available Merged Models ({fineTunedModels.length})</h3>
        {#if fineTunedModels.length === 0}
            <div class="no-models">
                <p>📭 No merged models found.</p>
                <p>Fine-tune a model first, and the merged model will automatically appear here after training completes.</p>
            </div>
        {:else}
            <div class="models-list">
                {#each fineTunedModels as model}
                    <div class="model-card">
                        <div class="model-header">
                            <h4>🤖 {model.name}</h4>
                            <!-- <span class="status-badge {model.model_type === 'RAG Model' ? 'status-ready' : 'status-simple'}">
                                {model.model_type === 'RAG Model' ? 'RAG' : 'Simple'}
                            </span> -->
                        </div>
                        
                        <div class="model-details">
                            <div class="detail-row">
                                <span class="label">Type:</span>
                                <span class="value">{model.model_type}</span>
                            </div>
                            <div class="detail-row">
                                <span class="label">Export ID:</span>
                                <span class="value">{model.export_id}</span>
                            </div>
                            {#if model.adapter_info}
                                <div class="detail-row">
                                    <span class="label">Adapter:</span>
                                    <span class="value">{model.adapter_info.adapter_name}</span>
                                </div>
                                <div class="detail-row">
                                    <span class="label">Base Model:</span>
                                    <span class="value">{model.adapter_info.base_model}</span>
                                </div>
                                <div class="detail-row">
                                    <span class="label">Training Date:</span>
                                    <span class="value">{new Date(model.adapter_info.created_at).toLocaleString()}</span>
                                </div>
                            {:else if model.rag_info}
                                <div class="detail-row">
                                    <span class="label">Adapter:</span>
                                    <span class="value">{model.rag_info.adapter_name}</span>
                                </div>
                                <div class="detail-row">
                                    <span class="label">Base Model:</span>
                                    <span class="value">{model.rag_info.base_model}</span>
                                </div>
                                <div class="detail-row">
                                    <span class="label">Created:</span>
                                    <span class="value">{new Date(model.rag_info.created_at).toLocaleString()}</span>
                                </div>
                            {:else}
                                <div class="detail-row">
                                    <span class="label">Size:</span>
                                    <span class="value">{(model.size / 1024 / 1024 / 1024).toFixed(2)} GB</span>
                                </div>
                                <div class="detail-row">
                                    <span class="label">Modified:</span>
                                    <span class="value">{new Date(model.modified_at).toLocaleString()}</span>
                                </div>
                            {/if}
                        </div>
                        
                        <div class="model-actions">
                            <button 
                                on:click={() => deleteModel(model.name)} 
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

    .status-simple {
        background: #fff3cd;
        color: #856404;
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