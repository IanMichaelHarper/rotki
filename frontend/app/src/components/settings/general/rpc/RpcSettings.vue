<script setup lang="ts">
import { Blockchain } from '@rotki/common/lib/blockchain';
import type { AsyncComponent, Ref } from 'vue';

const { t } = useI18n();

interface ChainRpcSettingTab {
  chain: Blockchain;
  component: AsyncComponent;
}

interface CustomRpcSettingTab {
  id: string;
  name: string;
  image: string;
  component: AsyncComponent;
}

type RpcSettingTab = ChainRpcSettingTab | CustomRpcSettingTab;

function isChain(item: RpcSettingTab): item is ChainRpcSettingTab {
  return 'chain' in item;
}

const rpcSettingTab: Ref<number> = ref(0);

const { txEvmChains } = useSupportedChains();
const evmChainTabs = useArrayMap(txEvmChains, (chain) => {
  assert(isOfEnum(Blockchain)(chain.id));
  return {
    chain: chain.id,
    component: defineAsyncComponent(
      () => import('@/components/settings/general/rpc/EvmRpcNodeManager.vue'),
    ),
  } satisfies RpcSettingTab;
});

const rpcSettingTabs = computed<RpcSettingTab[]>(() => [
  ...get(evmChainTabs),
  {
    chain: Blockchain.KSM,
    component: defineAsyncComponent(
      () => import('@/components/settings/general/rpc/KsmRpcSetting.vue'),
    ),
  },
  {
    chain: Blockchain.DOT,
    component: defineAsyncComponent(
      () => import('@/components/settings/general/rpc/DotRpcSetting.vue'),
    ),
  },
  {
    id: 'eth_consensus_layer',
    name: 'ETH Beacon Node',
    image: './assets/images/protocols/ethereum.svg',
    component: defineAsyncComponent(
      () => import('@/components/settings/general/rpc/BeaconchainRpcSetting.vue'),
    ),
  },
]);
</script>

<template>
  <RuiCard class="mt-8">
    <template #header>
      {{ t('general_settings.rpc_node_setting.title') }}
    </template>

    <div>
      <RuiTabs
        v-model="rpcSettingTab"
        color="primary"
        class="!h-auto"
      >
        <RuiTab
          v-for="tab in rpcSettingTabs"
          :key="isChain(tab) ? tab.chain : tab.id"
          class="!pb-3"
        >
          <LocationDisplay
            v-if="isChain(tab)"
            :open-details="false"
            :identifier="tab.chain"
          />

          <div
            v-else
            class="flex flex-col items-center gap-1"
          >
            <AppImage
              :src="tab.image"
              size="24px"
              contain
              class="icon-bg"
            />
            <span class="capitalize text-rui-text-secondary -mb-1">
              {{ tab.name }}
            </span>
          </div>
        </RuiTab>
      </RuiTabs>
      <RuiDivider class="mb-4" />
      <RuiTabItems v-model="rpcSettingTab">
        <template #default>
          <template
            v-for="tab in rpcSettingTabs"
          >
            <RuiTabItem
              :key="isChain(tab) ? tab.chain : tab.id"
            >
              <template #default>
                <Component
                  :is="tab.component"
                  v-if="isChain(tab)"
                  :chain="tab.chain"
                />
                <Component
                  :is="tab.component"
                  v-else
                />
              </template>
            </RuiTabItem>
          </template>
        </template>
      </RuiTabItems>
    </div>
  </RuiCard>
</template>
