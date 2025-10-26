<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();

	import { deleteContentById } from '$lib/apis/contents';
	import { mobile, showSidebar } from '$lib/stores';

	import GarbageBin from '$lib/components/icons/GarbageBin.svelte';

	export let id;
	export let title;

	const deleteContentHandler = async (id: string) => {
		const res = await deleteContentById(localStorage.token, id).catch((error) => {
			console.error(error);
			return null;
		});

		if (res) {
			// Refresh the content list
			dispatch('change');
		}
	};
</script>

<!-- svelte-ignore a11y-no-static-element-interactions -->
<div class="relative group">
	<a
		class="w-full flex justify-between rounded-lg px-[11px] py-[6px] hover:bg-gray-100 dark:hover:bg-gray-950 whitespace-nowrap text-ellipsis"
		href="/content-generator?id={id}"
		on:click={() => {
			if ($mobile) {
				showSidebar.set(false);
			}
		}}
	>
		<div class="flex self-center flex-1 w-full">
			<div dir="auto" class="text-left self-center overflow-hidden w-full h-[20px]">
				{title}
			</div>
		</div>
	</a>

	<!-- Delete button -->
	<div
		class="absolute right-1 top-[4px] py-1 pr-0.5 mr-1.5 pl-5 bg-gradient-to-l from-gray-100 dark:from-gray-950 from-80% to-transparent invisible group-hover:visible"
	>
		<div class="flex self-center z-10 items-end">
			<button
				aria-label="Delete Content"
				class="self-center dark:hover:text-white transition"
				on:click={(e) => {
					e.preventDefault();
					e.stopPropagation();
					deleteContentHandler(id);
				}}
			>
				<GarbageBin className="w-4 h-4" />
			</button>
		</div>
	</div>
</div>

