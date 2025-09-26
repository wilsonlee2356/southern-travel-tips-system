<script>
    import RAGManager from '$lib/components/RAGManager.svelte';
</script>

<svelte:head>
    <title>RAG Manager - Southern Travel Tips</title>
</svelte:head>

<div class="page-container">
    <div class="page-header">
        <h1>RAG Model Management</h1>
        <p>Manage your fine-tuned adapters for RAG (Retrieval Augmented Generation) integration with OpenWebUI.</p>
    </div>
    
    <RAGManager />
</div>

<style>
    .page-container {
        max-width: 1200px;
        margin: 0 auto;
        padding: 20px;
    }

    .page-header {
        text-align: center;
        margin-bottom: 30px;
        padding: 20px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
    }

    .page-header h1 {
        margin: 0 0 10px 0;
        font-size: 2.5em;
    }

    .page-header p {
        margin: 0;
        font-size: 1.1em;
        opacity: 0.9;
    }
</style>
