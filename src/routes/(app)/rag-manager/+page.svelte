<script>
    import RAGManager from '$lib/components/RAGManager.svelte';
    import { mobile, showSidebar, user, showArchivedChats } from '$lib/stores';
    import { getContext } from 'svelte';
    import UserMenu from '$lib/components/layout/Sidebar/UserMenu.svelte';
    import Tooltip from '$lib/components/common/Tooltip.svelte';
    import Sidebar from '$lib/components/icons/Sidebar.svelte';

    const i18n = getContext('i18n');
</script>

<svelte:head>
    <title>Fine-tuned Models Manager - Southern Travel Tips</title>
</svelte:head>

<div
	class=" flex flex-col w-full h-screen max-h-[100dvh] transition-width duration-200 ease-in-out {$showSidebar
		? 'md:max-w-[calc(100%-260px)]'
		: 'md:max-w-full'} md:ml-0"
>
	<nav class="   px-2 pt-1.5 backdrop-blur-xl w-full drag-region">
		<div class=" flex items-center">
			{#if $mobile}
				<div class="{$showSidebar ? 'md:hidden' : ''} flex flex-none items-center">
					<Tooltip
						content={$showSidebar ? $i18n.t('Close Sidebar') : $i18n.t('Open Sidebar')}
						interactive={true}
					>
						<button
							id="sidebar-toggle-button"
							class=" cursor-pointer flex rounded-lg hover:bg-gray-100 dark:hover:bg-gray-850 transition cursor-"
							on:click={() => {
								showSidebar.set(!$showSidebar);
							}}
						>
							<div class=" self-center p-1.5">
								<Sidebar />
							</div>
						</button>
					</Tooltip>
				</div>
			{/if}

			<div class="ml-2 py-0.5 self-center flex items-center justify-between w-full">
				<div class="">
					<div
						class="flex gap-1 scrollbar-none overflow-x-auto w-fit text-center text-sm font-medium bg-transparent py-1 touch-auto pointer-events-auto"
					>
						<a class="min-w-fit transition flex items-center gap-2" href="/rag-manager">
							<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" class="size-5 text-gray-900 dark:text-gray-100">
								<path
									d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
									fill="none"
									stroke="currentColor"
									stroke-width="1.5"
								/>
							</svg>
							{$i18n.t('Fine-tuned Models Manager')}
						</a>
					</div>
				</div>

				<div class=" self-center flex items-center gap-1">
					{#if $user !== undefined && $user !== null}
						<UserMenu
							className="max-w-[240px]"
							role={$user?.role}
							help={true}
							on:show={(e) => {
								if (e.detail === 'archived-chat') {
									showArchivedChats.set(true);
								}
							}}
						>
							<button
								class="select-none flex rounded-xl p-1.5 w-full hover:bg-gray-50 dark:hover:bg-gray-850 transition"
								aria-label="User Menu"
							>
								<div class=" self-center">
									<img
										src={$user?.profile_image_url}
										class="size-6 object-cover rounded-full"
										alt="User profile"
									/>
								</div>
								<div class="ml-2 text-left">
									<div class="text-xs font-medium text-gray-900 dark:text-white truncate">
										{$user?.name || $user?.email}
									</div>
								</div>
							</button>
						</UserMenu>
					{/if}
				</div>
			</div>
		</div>
	</nav>

	<div class="pb-1 flex-1 max-h-full overflow-y-auto @container">
		<div class="max-w-7xl mx-auto p-6">

			<!-- Main Content -->
			<RAGManager />
		</div>
	</div>
</div>
