/**
 * API utilities for adapter management
 */

const API_BASE_URL = 'http://localhost:8001';

/**
 * Fetch available adapters from the backend
 */
export async function fetchAdapters() {
    try {
        console.log('Fetching adapters from:', `${API_BASE_URL}/api/adapters/list`);
        const response = await fetch(`${API_BASE_URL}/api/adapters/list`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            },
            signal: AbortSignal.timeout(10000) // 10 second timeout
        });
        
        console.log('Adapters response status:', response.status);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('Adapters response data:', data);
        
        return {
            success: true,
            adapters: data.adapters || [],
            count: data.count || 0
        };
    } catch (error) {
        console.error('Error fetching adapters:', error);
        return {
            success: false,
            adapters: [],
            count: 0,
            error: error.message
        };
    }
}

/**
 * Fetch merged models from the backend
 */
export async function fetchMergedModels() {
    try {
        console.log('Fetching merged models from:', `${API_BASE_URL}/api/merged-models/list`);
        const response = await fetch(`${API_BASE_URL}/api/merged-models/list`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            },
            signal: AbortSignal.timeout(10000) // 10 second timeout
        });
        
        console.log('Merged models response status:', response.status);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('Merged models response data:', data);
        
        return {
            success: true,
            mergedModels: data.merged_models || [],
            count: data.count || 0
        };
    } catch (error) {
        console.error('Error fetching merged models:', error);
        return {
            success: false,
            mergedModels: [],
            count: 0,
            error: error.message
        };
    }
}

/**
 * Merge an adapter with a base model
 */
export async function mergeAdapter(adapterId, baseModel = null) {
    try {
        const response = await fetch(`${API_BASE_URL}/api/adapters/merge`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                adapter_id: adapterId,
                base_model: baseModel
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error merging adapter:', error);
        return {
            success: false,
            error: error.message
        };
    }
}

/**
 * Register a merged model with Ollama
 */
export async function registerMergedModelWithOllama(modelName) {
    try {
        const response = await fetch(`${API_BASE_URL}/api/merged-models/${modelName}/register-ollama`, {
            method: 'POST'
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error registering merged model with Ollama:', error);
        return {
            success: false,
            error: error.message
        };
    }
}

/**
 * Get inference information for a merged model
 */
export async function getInferenceInfo(modelName) {
    try {
        const response = await fetch(`${API_BASE_URL}/api/merged-models/${modelName}/inference-info`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error getting inference info:', error);
        return {
            success: false,
            error: error.message
        };
    }
}

/**
 * Generate text using a merged model
 */
export async function generateWithMergedModel(modelName, prompt) {
    try {
        const response = await fetch(`${API_BASE_URL}/api/inference/generate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                model_name: modelName,
                prompt: prompt
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error generating with merged model:', error);
        return {
            success: false,
            error: error.message
        };
    }
}

// RAG-specific functions
export async function createRAGModel(adapterId, baseModel = 'qwen2.5:14b') {
    try {
        const response = await fetch(`${API_BASE_URL}/api/rag/create-model`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                adapter_id: adapterId,
                base_model: baseModel
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to create RAG model');
        }

        return await response.json();
    } catch (error) {
        console.error('Error creating RAG model:', error);
        throw error;
    }
}

export async function fetchRAGModels() {
    try {
        console.log('Fetching RAG models from:', `${API_BASE_URL}/api/rag/models/list`);
        const response = await fetch(`${API_BASE_URL}/api/rag/models/list`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            },
            signal: AbortSignal.timeout(10000) // 10 second timeout
        });
        
        console.log('RAG models response status:', response.status);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        console.log('RAG models response data:', data);
        
        return {
            success: true,
            rag_models: data.rag_models || [],
            count: data.count || 0
        };
    } catch (error) {
        console.error('Error fetching RAG models:', error);
        return {
            success: false,
            rag_models: [],
            count: 0,
            error: error.message
        };
    }
}

// RAG Integration Helper Functions
export async function getCurrentRAGConfig() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/rag/current-config`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        return {
            success: true,
            config: data.config || {}
        };
    } catch (error) {
        console.error('Error fetching RAG config:', error);
        return {
            success: false,
            config: {},
            error: error.message
        };
    }
}

export async function testRAGModel(modelName, testQuery = "測試RAG功能") {
    try {
        const response = await fetch(`${API_BASE_URL}/api/rag/test-model`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                model_name: modelName,
                test_query: testQuery
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to test RAG model');
        }

        const data = await response.json();
        return {
            success: true,
            test_result: data.test_result || {},
            model_name: data.model_name,
            test_query: data.test_query
        };
    } catch (error) {
        console.error('Error testing RAG model:', error);
        return {
            success: false,
            error: error.message,
            model_name: modelName,
            test_query: testQuery
        };
    }
}

export async function deleteRAGModel(modelName) {
    try {
        console.log('Deleting RAG model:', modelName);
        const response = await fetch(`${API_BASE_URL}/api/rag/models/${encodeURIComponent(modelName)}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
            }
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to delete RAG model');
        }

        const data = await response.json();
        return {
            success: true,
            message: data.message,
            model_name: modelName
        };
    } catch (error) {
        console.error('Error deleting RAG model:', error);
        return {
            success: false,
            error: error.message,
            model_name: modelName
        };
    }
}
