/**
 * Fine-tuning utility functions for Ollama models
 */

// Configuration
const FINETUNING_CONFIG = {
	baseUrl: 'http://localhost:11434',
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
	 * Check if Ollama is running and accessible
	 * @returns {Promise<boolean>} Connection status
	 */
	async checkConnection() {
		try {
			const response = await fetch(`${this.config.baseUrl}/api/tags`, {
				method: 'GET',
				headers: {
					'Content-Type': 'application/json',
				},
			});
			return response.ok;
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
			const response = await fetch(`${this.config.baseUrl}/api/tags`);
			if (response.ok) {
				const data = await response.json();
				return data.models || [];
			}
		} catch (error) {
			console.error('Failed to get models:', error);
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

		try {
			// Update status
			if (this.callbacks.onStatusChange) {
				this.callbacks.onStatusChange(this.trainingStatus);
			}

			// In a real implementation, this would:
			// 1. Upload dataset to training server
			// 2. Start training job
			// 3. Monitor progress
			// 4. Handle completion/errors

			// For now, simulate the training process
			await this.simulateTraining(config, dataset);

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
	 * Simulate training process (for demonstration)
	 * @param {Object} config - Training configuration
	 * @param {File} _dataset - Dataset file (unused in simulation)
	 * @returns {Promise<void>}
	 */
	async simulateTraining(config, _dataset) {
		const totalSteps = config.numEpochs * 100; // Simulate 100 steps per epoch
		
		for (let epoch = 1; epoch <= config.numEpochs; epoch++) {
			this.trainingStatus = `Training epoch ${epoch}/${config.numEpochs}...`;
			
			if (this.callbacks.onStatusChange) {
				this.callbacks.onStatusChange(this.trainingStatus);
			}

			// Simulate epoch training
			for (let step = 0; step < 100; step++) {
				await new Promise(resolve => setTimeout(resolve, 50));
				
				const progress = ((epoch - 1) * 100 + step) / totalSteps;
				this.trainingProgress = progress * 100;
				
				// Simulate loss values
				const currentLoss = Math.max(0.1, 2.0 - (progress * 1.8) + Math.random() * 0.2);
				const validationLoss = Math.max(0.1, 2.2 - (progress * 1.9) + Math.random() * 0.3);
				
				if (this.callbacks.onProgress) {
					this.callbacks.onProgress({
						epoch,
						step,
						progress: this.trainingProgress,
						trainLoss: currentLoss,
						valLoss: validationLoss,
						learningRate: config.learningRate * Math.exp(-progress * 0.5)
					});
				}
			}
		}

		this.isTraining = false;
		this.trainingStatus = 'Training completed successfully!';
		this.trainingProgress = 100;

		if (this.callbacks.onComplete) {
			this.callbacks.onComplete({
				status: 'completed',
				message: 'Training completed successfully!'
			});
		}
	}

	/**
	 * Stop training process
	 */
	stopTraining() {
		this.isTraining = false;
		this.trainingStatus = 'Training stopped by user';
		
		if (this.callbacks.onStatusChange) {
			this.callbacks.onStatusChange(this.trainingStatus);
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
			// In a real implementation, this would export the model
			// For now, simulate export process
			await new Promise(resolve => setTimeout(resolve, 1000));
			
			return {
				success: true,
				message: `Model ${adapterName} exported successfully`,
				path: `./models/${adapterName}`
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
