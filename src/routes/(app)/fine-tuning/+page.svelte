<script>
	import { mobile, showSidebar, user, showArchivedChats } from '$lib/stores';
	import { getContext } from 'svelte';
	import { onMount } from 'svelte';
	import { FineTuningClient, FineTuningUtils } from '$lib/utils/fineTuning.js';

	const i18n = getContext('i18n');

	import UserMenu from '$lib/components/layout/Sidebar/UserMenu.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Sidebar from '$lib/components/icons/Sidebar.svelte';

	// Training state
	let isTraining = false;
	let trainingProgress = 0;
	let trainingStatus = '';
	let trainingHistory = [];
	let currentEpoch = 0;
	let totalEpochs = 0;
	let currentLoss = 0;
	let validationLoss = 0;
	let learningRate = 0;
	let trainingLogs = [];
	let currentSessionId = null;

	// Model configuration
	let modelConfig = {
		baseModel: 'qwen2.5:32b',
		adapterName: 'my-custom-adapter',
		learningRate: 0.0001,
		numEpochs: 3,
		batchSize: 4,
		gradientAccumulationSteps: 4,
		loraRank: 16,
		loraAlpha: 32,
		loraDropout: 0.1,
		targetModules: ['q_proj', 'v_proj', 'k_proj', 'o_proj'],
		datasetPath: '',
		outputPath: './models/fine-tuned'
	};

	// Dataset management
	let datasetFiles = [];
	let selectedDataset = null;

	// Available models
	let availableModels = [
		'qwen2.5:32b',
		'qwen2.5:14b',
	];

	// Chart data
	let lossChartData = [];
	let learningRateChartData = [];

	// Initialize fine-tuning client
	let fineTuningClient = new FineTuningClient();

	// Training functions
	const startTraining = async () => {
		if (!selectedDataset) {
			alert('Please select a dataset first');
			return;
		}

		// Validate configuration
		const validation = FineTuningUtils.validateConfig(modelConfig);
		if (!validation.isValid) {
			alert('Configuration errors:\n' + validation.errors.join('\n'));
			return;
		}

		try {
			// Set up callbacks
			fineTuningClient.setCallbacks({
				onProgress: (data) => {
					trainingProgress = data.progress;
					currentEpoch = data.epoch;
					currentLoss = data.trainLoss;
					validationLoss = data.valLoss;
					learningRate = data.learningRate;
					
					// Update charts
					lossChartData = [...lossChartData, {
						epoch: data.epoch + (data.step / 100),
						trainLoss: data.trainLoss,
						valLoss: data.valLoss
					}];

					learningRateChartData = [...learningRateChartData, {
						epoch: data.epoch + (data.step / 100),
						lr: data.learningRate
					}];

					// Limit chart data
					if (lossChartData.length > 100) {
						lossChartData = lossChartData.slice(-100);
						learningRateChartData = learningRateChartData.slice(-100);
					}
				},
				onStatusChange: (status) => {
					trainingStatus = status;
				},
				onComplete: (result) => {
					trainingStatus = result.message;
					isTraining = false;
					
					// Add final epoch to history
					trainingHistory = [...trainingHistory, {
						epoch: modelConfig.numEpochs,
						trainLoss: currentLoss,
						valLoss: validationLoss,
						timestamp: new Date().toLocaleTimeString()
					}];
				},
				onError: (error) => {
					trainingStatus = 'Training failed: ' + error.message;
					isTraining = false;
				}
			});

			// Start training
			console.log('Starting training...');
			const sessionId = await fineTuningClient.startFineTuning(modelConfig, selectedDataset);
			console.log('Received session ID:', sessionId);
			currentSessionId = sessionId;
			trainingLogs = [`[${new Date().toLocaleTimeString()}] Training started with session ID: ${sessionId}`];
		} catch (error) {
			console.error('Training failed:', error);
			trainingStatus = 'Training failed: ' + error.message;
			isTraining = false;
		}
	};

	const stopTraining = () => {
		fineTuningClient.stopTraining();
		isTraining = false;
		trainingStatus = 'Training stopped by user';
	};

	const uploadDataset = (event) => {
		const files = Array.from(event.target.files);
		datasetFiles = [...datasetFiles, ...files];
	};

	const selectDataset = (file) => {
		selectedDataset = file;
		modelConfig.datasetPath = file.name;
	};

	const removeDataset = (file) => {
		datasetFiles = datasetFiles.filter(f => f !== file);
		if (selectedDataset === file) {
			selectedDataset = null;
			modelConfig.datasetPath = '';
		}
	};

	const exportModel = async () => {
		try {
			const result = await fineTuningClient.exportModel(modelConfig.adapterName);
			alert(result.message);
		} catch (error) {
			alert('Export failed: ' + error.message);
		}
	};

	const refreshLogs = async () => {
		if (currentSessionId && currentSessionId !== 'undefined') {
			try {
				const response = await fetch(`http://localhost:8001/api/fine-tuning/status/${currentSessionId}`);
				if (response.ok) {
					const status = await response.json();
					const newLog = `[${new Date().toLocaleTimeString()}] ${status.message} (Loss: ${status.train_loss?.toFixed(4) || 'N/A'})`;
					trainingLogs = [...trainingLogs, newLog].slice(-50); // Keep last 50 logs
				} else {
					const errorLog = `[${new Date().toLocaleTimeString()}] Failed to fetch status: ${response.status}`;
					trainingLogs = [...trainingLogs, errorLog].slice(-50);
				}
			} catch (error) {
				const errorLog = `[${new Date().toLocaleTimeString()}] Error fetching logs: ${error.message}`;
				trainingLogs = [...trainingLogs, errorLog].slice(-50);
				console.error('Failed to fetch logs:', error);
			}
		} else {
			const noSessionLog = `[${new Date().toLocaleTimeString()}] No active training session`;
			trainingLogs = [...trainingLogs, noSessionLog].slice(-50);
		}
	};

	const downloadTrainingLog = () => {
		const logData = {
			config: modelConfig,
			history: trainingHistory,
			charts: {
				loss: lossChartData,
				learningRate: learningRateChartData
			},
			logs: trainingLogs
		};
		
		const blob = new Blob([JSON.stringify(logData, null, 2)], { type: 'application/json' });
		const url = URL.createObjectURL(blob);
		const a = document.createElement('a');
		a.href = url;
		a.download = `training-log-${Date.now()}.json`;
		a.click();
		URL.revokeObjectURL(url);
	};

	onMount(() => {
		// Initialize with some sample data
		lossChartData = [];
		learningRateChartData = [];
		
		// Set up automatic log refresh during training
		const logInterval = setInterval(() => {
			if (isTraining && currentSessionId) {
				refreshLogs();
			}
		}, 3000); // Refresh every 3 seconds
		
		// Cleanup interval on component destroy
		return () => clearInterval(logInterval);
	});
</script>

<div
	class=" flex flex-col w-full h-screen max-h-[100dvh] transition-width duration-200 ease-in-out {$showSidebar
		? 'md:max-w-[calc(100%-260px)]'
		: 'md:max-w-full'} md:ml-0"
>
	<!-- Header -->
	<div class="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
		<div class="flex items-center space-x-4">
			{#if $mobile}
				<button
					class="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition"
					on:click={() => ($showSidebar = !$showSidebar)}
				>
					<Sidebar className="size-5" />
				</button>
			{/if}
			<h1 class="text-2xl font-bold text-gray-900 dark:text-white">
				{$i18n.t('Model Fine-tuning')}
			</h1>
		</div>
		<UserMenu />
	</div>

	<!-- Main Content -->
	<div class="flex-1 overflow-y-auto">
		<div class="min-h-full grid grid-cols-1 lg:grid-cols-3 gap-6 p-6">
			<!-- Left Panel: Configuration -->
			<div class="lg:col-span-1 space-y-6 overflow-y-auto">
				<!-- Model Configuration -->
				<div class="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
					<h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">Model Configuration</h2>
					
					<div class="space-y-4">
						<!-- Base Model -->
						<div>
							<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
								Base Model
							</label>
							<select
								bind:value={modelConfig.baseModel}
								class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
							>
								{#each availableModels as model}
									<option value={model}>{model}</option>
								{/each}
							</select>
						</div>

						<!-- Adapter Name -->
						<div>
							<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
								Adapter Name
							</label>
							<input
								type="text"
								bind:value={modelConfig.adapterName}
								class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
								placeholder="my-custom-adapter"
							/>
						</div>

						<!-- Learning Rate -->
						<div>
							<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
								Learning Rate: {modelConfig.learningRate}
							</label>
							<input
								type="range"
								min="0.00001"
								max="0.01"
								step="0.00001"
								bind:value={modelConfig.learningRate}
								class="w-full"
							/>
						</div>

						<!-- Number of Epochs -->
						<div>
							<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
								Number of Epochs: {modelConfig.numEpochs}
							</label>
							<input
								type="range"
								min="1"
								max="10"
								step="1"
								bind:value={modelConfig.numEpochs}
								class="w-full"
							/>
						</div>

						<!-- Batch Size -->
						<div>
							<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
								Batch Size: {modelConfig.batchSize}
							</label>
							<input
								type="range"
								min="1"
								max="16"
								step="1"
								bind:value={modelConfig.batchSize}
								class="w-full"
							/>
						</div>

						<!-- LoRA Rank -->
						<div>
							<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
								LoRA Rank: {modelConfig.loraRank}
							</label>
							<input
								type="range"
								min="4"
								max="64"
								step="4"
								bind:value={modelConfig.loraRank}
								class="w-full"
							/>
						</div>

						<!-- LoRA Alpha -->
						<div>
							<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
								LoRA Alpha: {modelConfig.loraAlpha}
							</label>
							<input
								type="range"
								min="8"
								max="128"
								step="8"
								bind:value={modelConfig.loraAlpha}
								class="w-full"
							/>
						</div>
					</div>
				</div>

				<!-- Dataset Management -->
				<div class="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
					<h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">Dataset Management</h2>
					
					<div class="space-y-4">
						<!-- Upload Dataset -->
						<div>
							<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
								Upload Dataset
							</label>
							<input
								type="file"
								multiple
								accept=".json,.jsonl,.txt,.csv"
								on:change={uploadDataset}
								class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
							/>
						</div>

						<!-- Dataset List -->
						{#if datasetFiles.length > 0}
							<div class="space-y-2">
								<label class="block text-sm font-medium text-gray-700 dark:text-gray-300">
									Available Datasets
								</label>
								{#each datasetFiles as file}
									<div class="flex items-center justify-between p-2 bg-gray-50 dark:bg-gray-700 rounded">
										<button
											class="flex-1 text-left text-sm {selectedDataset === file ? 'text-blue-600 font-medium' : 'text-gray-700 dark:text-gray-300'}"
											on:click={() => selectDataset(file)}
										>
											{file.name}
										</button>
										<button
											class="ml-2 text-red-500 hover:text-red-700"
											on:click={() => removeDataset(file)}
										>
											<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
											</svg>
										</button>
									</div>
								{/each}
							</div>
						{/if}
					</div>
				</div>

				<!-- Training Controls -->
				<div class="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
					<h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">Training Controls</h2>
					
					<div class="space-y-4">
						{#if !isTraining}
							<button
								class="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-3 px-4 rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed"
								disabled={!selectedDataset}
								on:click={startTraining}
							>
								<svg class="w-5 h-5 mr-2 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.828 14.828a4 4 0 01-5.656 0M9 10h1m4 0h1m-6 4h1m4 0h1m-6-8h8a2 2 0 012 2v8a2 2 0 01-2 2H8a2 2 0 01-2-2v-4a2 2 0 012-2z"></path>
								</svg>
								Start Training
							</button>
						{:else}
							<button
								class="w-full bg-red-600 hover:bg-red-700 text-white font-medium py-3 px-4 rounded-lg transition"
								on:click={stopTraining}
							>
								<svg class="w-5 h-5 mr-2 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 10h6v4H9z"></path>
								</svg>
								Stop Training
							</button>
						{/if}

						<button
							class="w-full bg-gray-600 hover:bg-gray-700 text-white font-medium py-3 px-4 rounded-lg transition"
							on:click={exportModel}
						>
							<svg class="w-5 h-5 mr-2 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
							</svg>
							Export Model
						</button>

						<button
							class="w-full bg-green-600 hover:bg-green-700 text-white font-medium py-3 px-4 rounded-lg transition"
							on:click={downloadTrainingLog}
						>
							<svg class="w-5 h-5 mr-2 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
							</svg>
							Download Training Log
						</button>
					</div>
				</div>
			</div>

			<!-- Right Panel: Monitoring -->
			<div class="lg:col-span-2 space-y-6 overflow-y-auto">
				<!-- Training Logs -->
				<div class="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
					<div class="flex justify-between items-center mb-4">
						<h2 class="text-lg font-semibold text-gray-900 dark:text-white">Training Logs</h2>
						<button
							class="text-sm bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded"
							on:click={refreshLogs}
						>
							Refresh
						</button>
					</div>
					
					<div class="bg-black text-green-400 font-mono text-xs p-4 rounded-lg h-64 overflow-y-auto">
						{#if trainingLogs.length > 0}
							{#each trainingLogs as log}
								<div class="mb-1">{log}</div>
							{/each}
						{:else}
							<div class="text-gray-500">No logs available. Start training to see logs here.</div>
						{/if}
					</div>
				</div>

				<!-- Training Progress -->
				<div class="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
					<h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">Training Progress</h2>
					
					{#if isTraining || trainingProgress > 0}
						<div class="space-y-4">
							<!-- Progress Bar -->
							<div>
								<div class="flex justify-between text-sm text-gray-600 dark:text-gray-400 mb-2">
									<span>Progress</span>
									<span>{Math.round(trainingProgress)}%</span>
								</div>
								<div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
									<div
										class="bg-blue-600 h-2 rounded-full transition-all duration-300"
										style="width: {trainingProgress}%"
									></div>
								</div>
							</div>

							<!-- Status -->
							<div class="text-sm text-gray-600 dark:text-gray-400">
								<strong>Status:</strong> {trainingStatus}
							</div>

							<!-- Current Metrics -->
							<div class="grid grid-cols-2 md:grid-cols-4 gap-4">
								<div class="text-center">
									<div class="text-2xl font-bold text-blue-600">{currentEpoch}/{totalEpochs}</div>
									<div class="text-sm text-gray-600 dark:text-gray-400">Epochs</div>
								</div>
								<div class="text-center">
									<div class="text-2xl font-bold text-green-600">{currentLoss.toFixed(4)}</div>
									<div class="text-sm text-gray-600 dark:text-gray-400">Train Loss</div>
								</div>
								<div class="text-center">
									<div class="text-2xl font-bold text-orange-600">{validationLoss.toFixed(4)}</div>
									<div class="text-sm text-gray-600 dark:text-gray-400">Val Loss</div>
								</div>
								<div class="text-center">
									<div class="text-2xl font-bold text-purple-600">{learningRate.toFixed(6)}</div>
									<div class="text-sm text-gray-600 dark:text-gray-400">Learning Rate</div>
								</div>
							</div>
						</div>
					{:else}
						<div class="text-center text-gray-500 dark:text-gray-400 py-8">
							<svg class="w-16 h-16 mx-auto mb-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path>
							</svg>
							<p>No training in progress</p>
							<p class="text-sm">Configure your model and start training to see progress</p>
						</div>
					{/if}
				</div>

				<!-- Loss Chart -->
				<div class="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
					<h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">Training Loss</h2>
					
					{#if lossChartData.length > 0}
						<div class="h-64 bg-gray-50 dark:bg-gray-900 rounded-lg p-4">
							<!-- Simple SVG chart for demonstration -->
							<svg class="w-full h-full" viewBox="0 0 400 200">
								{#each lossChartData as point, i}
									{#if i > 0}
										<line
											x1={((i - 1) / (lossChartData.length - 1)) * 380 + 10}
											y1={200 - (lossChartData[i - 1].trainLoss / 3) * 180 - 10}
											x2={(i / (lossChartData.length - 1)) * 380 + 10}
											y2={200 - (point.trainLoss / 3) * 180 - 10}
											stroke="#3B82F6"
											stroke-width="2"
											fill="none"
										/>
										<line
											x1={((i - 1) / (lossChartData.length - 1)) * 380 + 10}
											y1={200 - (lossChartData[i - 1].valLoss / 3) * 180 - 10}
											x2={(i / (lossChartData.length - 1)) * 380 + 10}
											y2={200 - (point.valLoss / 3) * 180 - 10}
											stroke="#F59E0B"
											stroke-width="2"
											fill="none"
										/>
									{/if}
								{/each}
								
								<!-- Legend -->
								<text x="10" y="20" class="text-xs fill-blue-600">Train Loss</text>
								<text x="10" y="35" class="text-xs fill-orange-600">Validation Loss</text>
							</svg>
						</div>
					{:else}
						<div class="h-64 flex items-center justify-center text-gray-500 dark:text-gray-400">
							<p>Loss chart will appear during training</p>
						</div>
					{/if}
				</div>

				<!-- Training History -->
				<div class="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
					<h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">Training History</h2>
					
					{#if trainingHistory.length > 0}
						<div class="overflow-x-auto">
							<table class="w-full text-sm">
								<thead>
									<tr class="border-b border-gray-200 dark:border-gray-700">
										<th class="text-left py-2">Epoch</th>
										<th class="text-left py-2">Train Loss</th>
										<th class="text-left py-2">Val Loss</th>
										<th class="text-left py-2">Time</th>
									</tr>
								</thead>
								<tbody>
									{#each trainingHistory as record}
										<tr class="border-b border-gray-100 dark:border-gray-800">
											<td class="py-2">{record.epoch}</td>
											<td class="py-2">{record.trainLoss.toFixed(4)}</td>
											<td class="py-2">{record.valLoss.toFixed(4)}</td>
											<td class="py-2">{record.timestamp}</td>
										</tr>
									{/each}
								</tbody>
							</table>
						</div>
					{:else}
						<div class="text-center text-gray-500 dark:text-gray-400 py-8">
							<p>No training history available</p>
						</div>
					{/if}
				</div>
			</div>
		</div>
	</div>
</div>
