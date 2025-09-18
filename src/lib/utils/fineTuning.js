/**
 * Fine-tuning utility functions for Ollama models
 */

// Configuration
const FINETUNING_CONFIG = {
	baseUrl: 'http://localhost:11434', // Ollama Docker container
	apiUrl: 'http://localhost:8001', // Fine-tuning API URL (Windows)
	timeout: 30000,
	defaultConfig: {
		learningRate: 0.0001,
		numEpochs: 3,
		batchSize: 4,
		gradientAccumulationSteps: 4,
		loraRank: 16,
		loraAlpha: 32,
		loraDropout: 0.1,
		targetModules: ['q_proj', 'v_proj', 'k_proj', 'o_proj']
	}
};

/**
 * Fine-tuning client class
 */
export class FineTuningClient {
	constructor(config = {}) {
		this.config = { ...FINETUNING_CONFIG, ...config };
		this.isTraining = false;
		this.trainingProgress = 0;
		this.trainingStatus = '';
		this.callbacks = {
			onProgress: null,
			onStatusChange: null,
			onComplete: null,
			onError: null
		};
	}

	/**
	 * Set callback functions for training events
	 * @param {Object} callbacks - Callback functions
	 */
	setCallbacks(callbacks) {
		this.callbacks = { ...this.callbacks, ...callbacks };
	}

	/**
	 * Check if Ollama and fine-tuning API are running and accessible
	 * @returns {Promise<boolean>} Connection status
	 */
	async checkConnection() {
		try {
			// Check Ollama
			const ollamaResponse = await fetch(`${this.config.baseUrl}/api/tags`, {
				method: 'GET',
				headers: {
					'Content-Type': 'application/json',
				},
			});
			
			// Check fine-tuning API
			const apiResponse = await fetch(`${this.config.apiUrl}/health`, {
				method: 'GET',
				headers: {
					'Content-Type': 'application/json',
				},
			});
			
			return ollamaResponse.ok && apiResponse.ok;
		} catch (error) {
			console.error('Connection check failed:', error);
			return false;
		}
	}

	/**
	 * Get list of available models
	 * @returns {Promise<Array>} List of available models
	 */
	async getAvailableModels() {
		try {
			// Get models from fine-tuning API (includes fine-tuned models)
			const response = await fetch(`${this.config.apiUrl}/api/models`);
			if (response.ok) {
				const data = await response.json();
				return data.models || [];
			}
		} catch (error) {
			console.error('Failed to get models:', error);
		}
		
		// Fallback to Ollama API
		try {
			const response = await fetch(`${this.config.baseUrl}/api/tags`);
			if (response.ok) {
				const data = await response.json();
				return data.models || [];
			}
		} catch (error) {
			console.error('Failed to get models from Ollama:', error);
		}
		
		return [];
	}

	/**
	 * Validate dataset format
	 * @param {File} file - Dataset file
	 * @returns {Promise<boolean>} Validation result
	 */
	async validateDataset(file) {
		try {
			const text = await file.text();
			
			// Check if it's JSON Lines format
			if (file.name.endsWith('.jsonl')) {
				const lines = text.split('\n').filter(line => line.trim());
				for (const line of lines) {
					try {
						const parsed = JSON.parse(line);
						if (!parsed.prompt || !parsed.response) {
							return false;
						}
					} catch {
						return false;
					}
				}
				return true;
			}
			
			// Check if it's JSON array format
			if (file.name.endsWith('.json')) {
				const parsed = JSON.parse(text);
				if (!Array.isArray(parsed)) {
					return false;
				}
				for (const item of parsed) {
					if (!item.prompt || !item.response) {
						return false;
					}
				}
				return true;
			}
			
			return false;
		} catch (error) {
			console.error('Dataset validation failed:', error);
			return false;
		}
	}

	/**
	 * Start fine-tuning process
	 * @param {Object} config - Training configuration
	 * @param {File} dataset - Dataset file
	 * @returns {Promise<void>}
	 */
	async startFineTuning(config, dataset) {
		if (this.isTraining) {
			throw new Error('Training is already in progress');
		}

		// Validate dataset
		const isValid = await this.validateDataset(dataset);
		if (!isValid) {
			throw new Error('Invalid dataset format. Expected JSON or JSONL with prompt/response fields.');
		}

		this.isTraining = true;
		this.trainingProgress = 0;
		this.trainingStatus = 'Initializing training...';
		this.currentSessionId = null;

		try {
			// Update status
			if (this.callbacks.onStatusChange) {
				this.callbacks.onStatusChange(this.trainingStatus);
			}

			// Start real training via API
			const sessionId = await this.startTrainingSession(config, dataset);
			this.currentSessionId = sessionId;

			// Start monitoring training progress (non-blocking)
			this.monitorTraining(sessionId);

			// Return session ID for frontend use
			return sessionId;

		} catch (error) {
			this.isTraining = false;
			this.trainingStatus = 'Training failed';
			
			if (this.callbacks.onError) {
				this.callbacks.onError(error);
			}
			throw error;
		}
	}

	/**
	 * Start training session via API
	 * @param {Object} config - Training configuration
	 * @param {File} dataset - Dataset file
	 * @returns {Promise<string>} Session ID
	 */
	async startTrainingSession(config, dataset) {
		const formData = new FormData();
		
		// Add dataset file
		formData.append('file', dataset);
		
		// Build query parameters
		const queryParams = new URLSearchParams({
			base_model: config.baseModel,
			adapter_name: config.adapterName,
			learning_rate: config.learningRate.toString(),
			num_epochs: config.numEpochs.toString(),
			batch_size: config.batchSize.toString(),
			gradient_accumulation_steps: config.gradientAccumulationSteps.toString(),
			lora_rank: config.loraRank.toString(),
			lora_alpha: config.loraAlpha.toString(),
			lora_dropout: config.loraDropout.toString(),
			target_modules: JSON.stringify(config.targetModules)
		});

		const response = await fetch(`${this.config.apiUrl}/api/fine-tuning/start?${queryParams}`, {
			method: 'POST',
			body: formData
		});

		if (!response.ok) {
			let errorMessage = 'Failed to start training';
			try {
				const error = await response.json();
				errorMessage = error.detail || error.message || JSON.stringify(error);
			} catch (e) {
				const errorText = await response.text();
				errorMessage = errorText || `HTTP ${response.status}: ${response.statusText}`;
			}
			console.error('Training API Error:', {
				status: response.status,
				statusText: response.statusText,
				error: errorMessage
			});
			throw new Error(`Training failed (${response.status}): ${errorMessage}`);
		}

		const result = await response.json();
		return result.session_id;
	}

	/**
	 * Monitor training progress
	 * @param {string} sessionId - Training session ID
	 * @returns {Promise<void>}
	 */
	async monitorTraining(sessionId) {
		const pollInterval = 2000; // Poll every 2 seconds
		
		while (this.isTraining && this.currentSessionId === sessionId) {
			try {
				const response = await fetch(`${this.config.apiUrl}/api/fine-tuning/status/${sessionId}`);
				
				if (!response.ok) {
					throw new Error('Failed to get training status');
				}

				const status = await response.json();
				
				// Update progress
				this.trainingProgress = status.progress;
				this.trainingStatus = status.message;
				
				if (this.callbacks.onProgress) {
					this.callbacks.onProgress({
						epoch: status.current_epoch,
						progress: status.progress,
						trainLoss: status.train_loss,
						valLoss: status.validation_loss,
						learningRate: status.learning_rate
					});
				}

				if (this.callbacks.onStatusChange) {
					this.callbacks.onStatusChange(status.message);
				}

				// Check if training is complete
				if (status.status === 'completed') {
					this.isTraining = false;
					this.trainingProgress = 100;
					
					if (this.callbacks.onComplete) {
						this.callbacks.onComplete({
							status: 'completed',
							message: status.message,
							sessionId: sessionId
						});
					}
					break;
				}

				// Check if training failed
				if (status.status === 'failed') {
					this.isTraining = false;
					
					if (this.callbacks.onError) {
						this.callbacks.onError(new Error(status.error || status.message));
					}
					break;
				}

				// Check if training was stopped
				if (status.status === 'stopped') {
					this.isTraining = false;
					
					if (this.callbacks.onComplete) {
						this.callbacks.onComplete({
							status: 'stopped',
							message: status.message,
							sessionId: sessionId
						});
					}
					break;
				}

				// Wait before next poll
				await new Promise(resolve => setTimeout(resolve, pollInterval));

			} catch (error) {
				console.error('Error monitoring training:', error);
				this.isTraining = false;
				
				if (this.callbacks.onError) {
					this.callbacks.onError(error);
				}
				break;
			}
		}
	}

	/**
	 * Stop training process
	 */
	async stopTraining() {
		if (this.currentSessionId) {
			try {
				const response = await fetch(`${this.config.apiUrl}/api/fine-tuning/stop/${this.currentSessionId}`, {
					method: 'POST'
				});

				if (response.ok) {
					this.isTraining = false;
					this.trainingStatus = 'Training stopped by user';
					
					if (this.callbacks.onStatusChange) {
						this.callbacks.onStatusChange(this.trainingStatus);
					}
				}
			} catch (error) {
				console.error('Error stopping training:', error);
			}
		} else {
			this.isTraining = false;
			this.trainingStatus = 'Training stopped by user';
			
			if (this.callbacks.onStatusChange) {
				this.callbacks.onStatusChange(this.trainingStatus);
			}
		}
	}

	/**
	 * Get training status
	 * @returns {Object} Current training status
	 */
	getTrainingStatus() {
		return {
			isTraining: this.isTraining,
			progress: this.trainingProgress,
			status: this.trainingStatus
		};
	}

	/**
	 * Export fine-tuned model
	 * @param {string} adapterName - Name of the adapter
	 * @returns {Promise<Object>} Export result
	 */
	async exportModel(adapterName) {
		try {
			// Check if model exists in Ollama
			const models = await this.getAvailableModels();
			const modelExists = models.some(model => model.name === adapterName);
			
			if (!modelExists) {
				throw new Error(`Model ${adapterName} not found. Please ensure training completed successfully.`);
			}
			
			// Model is already available in Ollama after successful training
			return {
				success: true,
				message: `Model ${adapterName} is ready for use in Ollama`,
				modelName: adapterName,
				usage: `ollama run ${adapterName}`
			};
		} catch (error) {
			console.error('Model export failed:', error);
			throw error;
		}
	}

	/**
	 * List available fine-tuned models
	 * @returns {Promise<Array>} List of available models
	 */
	async listFineTunedModels() {
		try {
			// In a real implementation, this would list available fine-tuned models
			// For now, return empty array
			return [];
		} catch (error) {
			console.error('Failed to list models:', error);
			return [];
		}
	}

	/**
	 * Delete fine-tuned model
	 * @param {string} modelName - Name of the model to delete
	 * @returns {Promise<boolean>} Deletion result
	 */
	async deleteModel(modelName) {
		try {
			// In a real implementation, this would delete the model
			console.log(`Deleting model: ${modelName}`);
			return true;
		} catch (error) {
			console.error('Model deletion failed:', error);
			return false;
		}
	}
}

/**
 * Utility functions for fine-tuning
 */
export const FineTuningUtils = {
	/**
	 * Create default training configuration
	 * @param {Object} overrides - Configuration overrides
	 * @returns {Object} Training configuration
	 */
	createDefaultConfig(overrides = {}) {
		return {
			...FINETUNING_CONFIG.defaultConfig,
			...overrides
		};
	},

	/**
	 * Validate training configuration
	 * @param {Object} config - Configuration to validate
	 * @returns {Object} Validation result
	 */
	validateConfig(config) {
		const errors = [];

		if (!config.baseModel) {
			errors.push('Base model is required');
		}

		if (!config.adapterName) {
			errors.push('Adapter name is required');
		}

		if (config.learningRate <= 0 || config.learningRate > 1) {
			errors.push('Learning rate must be between 0 and 1');
		}

		if (config.numEpochs <= 0 || config.numEpochs > 100) {
			errors.push('Number of epochs must be between 1 and 100');
		}

		if (config.batchSize <= 0 || config.batchSize > 32) {
			errors.push('Batch size must be between 1 and 32');
		}

		if (config.loraRank <= 0 || config.loraRank > 128) {
			errors.push('LoRA rank must be between 1 and 128');
		}

		return {
			isValid: errors.length === 0,
			errors
		};
	},

	/**
	 * Generate training command for Ollama
	 * @param {Object} config - Training configuration
	 * @param {string} _datasetPath - Path to dataset (unused)
	 * @returns {string} Training command
	 */
	generateTrainingCommand(config, _datasetPath) {
		return `ollama create ${config.adapterName} -f Modelfile --from ${config.baseModel}`;
	},

	/**
	 * Format file size
	 * @param {number} bytes - File size in bytes
	 * @returns {string} Formatted file size
	 */
	formatFileSize(bytes) {
		const sizes = ['Bytes', 'KB', 'MB', 'GB'];
		if (bytes === 0) return '0 Bytes';
		const i = Math.floor(Math.log(bytes) / Math.log(1024));
		return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
	},

	/**
	 * Estimate training time
	 * @param {Object} config - Training configuration
	 * @param {number} datasetSize - Dataset size in MB
	 * @returns {number} Estimated time in minutes
	 */
	estimateTrainingTime(config, datasetSize) {
		// Rough estimation based on configuration
		const baseTime = datasetSize * 0.1; // 0.1 minutes per MB
		const epochMultiplier = config.numEpochs;
		const complexityMultiplier = config.loraRank / 16; // Based on LoRA rank
		
		return Math.round(baseTime * epochMultiplier * complexityMultiplier);
	}
};

// Default export
export default FineTuningClient;
