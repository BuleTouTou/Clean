<script setup lang="ts">
// @ts-nocheck
import { ref } from "vue";
import { useMutation, useQuery, useQueryClient } from "@tanstack/vue-query";
import {
  NAlert,
  NButton,
  NCard,
  NDatePicker,
  NRadio,
  NRadioGroup,
  NResult,
  NSelect,
  NSpace,
  NSpin,
  NTag,
  useMessage,
} from "naive-ui";
import { api, type BatchKind, type SheetInfo } from "../api";

const message = useMessage();
const queryClient = useQueryClient();
const kind = ref<BatchKind | null>(null);
const taskId = ref("");
const step = ref(1);
const busy = ref(false);
const file = ref<File | null>(null);
const sheets = ref<SheetInfo[]>([]);
const targets = ref<string[]>([]);
const suggestions = ref<any[]>([]);
const mapping = ref<Record<string, string>>({});
const estateReviews = ref<any[]>([]);
const estateSelected = ref<Record<string, string>>({});
const buildingReviews = ref<any[]>([]);
const buildingSelected = ref<Record<string, string>>({});
const entrustDate = ref(Date.now());
const exportResult = ref<any>(null);

useQuery({
  queryKey: ["status"],
  queryFn: () => api.status(),
  staleTime: 30_000,
});

const createTaskMutation = useMutation({ mutationFn: (value: BatchKind) => api.createTask(value) });
const uploadMutation = useMutation({ mutationFn: ({ id, source }: { id: string; source: File }) => api.upload(id, source) });
const selectSheetMutation = useMutation({ mutationFn: ({ id, sheet }: { id: string; sheet: SheetInfo }) => api.selectSheet(id, sheet) });
const mappingMutation = useMutation({ mutationFn: ({ id, value }: { id: string; value: Record<string, string> }) => api.mapping(id, value) });
const buildingReviewMutation = useMutation({ mutationFn: ({ id, value }: { id: string; value: Record<string, string> }) => api.buildingReview(id, value) });
const buildingConfirmMutation = useMutation({ mutationFn: ({ id, value, date }: { id: string; value: Record<string, string>; date: string }) => api.buildingConfirm(id, value, date) });
const exportMutation = useMutation({ mutationFn: ({ id, cleanOnly }: { id: string; cleanOnly: boolean }) => api.export(id, cleanOnly) });

function resetTask() {
  taskId.value = "";
  step.value = 1;
  file.value = null;
  sheets.value = [];
  suggestions.value = [];
  mapping.value = {};
  estateReviews.value = [];
  estateSelected.value = {};
  buildingReviews.value = [];
  buildingSelected.value = {};
  exportResult.value = null;
}

function handleFileChange(event: Event) {
  const input = event.target as HTMLInputElement;
  file.value = input.files?.[0] ?? null;
  upload();
}

async function createTask() {
  if (!kind.value) return;
  busy.value = true;
  try {
    const result = await createTaskMutation.mutateAsync(kind.value);
    taskId.value = result.taskId;
    step.value = 2;
    message.success("清洗任务已创建");
  } catch (error: any) {
    message.error(error.message);
  } finally {
    busy.value = false;
  }
}

async function upload() {
  if (!file.value || !taskId.value) return;
  busy.value = true;
  try {
    const result = await uploadMutation.mutateAsync({ id: taskId.value, source: file.value });
    sheets.value = result.sheets;
    message.success("文件识别完成");
  } catch (error: any) {
    message.error(error.message);
  } finally {
    busy.value = false;
  }
}

async function selectSheet(sheet: SheetInfo) {
  busy.value = true;
  try {
    const result = await selectSheetMutation.mutateAsync({ id: taskId.value, sheet });
    targets.value = result.targets;
    suggestions.value = result.suggestions;
    mapping.value = Object.fromEntries(result.suggestions.map((item: any) => [item.source, item.target || "__ignore__"]));
    step.value = 3;
  } catch (error: any) {
    message.error(error.message);
  } finally {
    busy.value = false;
  }
}

async function confirmMapping() {
  busy.value = true;
  try {
    const result = await mappingMutation.mutateAsync({ id: taskId.value, value: mapping.value });
    estateReviews.value = result.reviews;
    estateSelected.value = {};
    step.value = 4;
    message.success(`已自动匹配 ${result.autoCount} 个小区`);
  } catch (error: any) {
    message.error(error.message);
  } finally {
    busy.value = false;
  }
}

async function confirmEstate() {
  busy.value = true;
  try {
    const result = await buildingReviewMutation.mutateAsync({ id: taskId.value, value: estateSelected.value });
    buildingReviews.value = result.reviews;
    buildingSelected.value = {};
    step.value = 5;
  } catch (error: any) {
    message.error(error.message);
  } finally {
    busy.value = false;
  }
}

async function confirmBuilding() {
  busy.value = true;
  try {
    await buildingConfirmMutation.mutateAsync({
      id: taskId.value,
      value: buildingSelected.value,
      date: new Date(entrustDate.value).toISOString().slice(0, 10),
    });
    step.value = 6;
  } catch (error: any) {
    message.error(error.message);
  } finally {
    busy.value = false;
  }
}

async function exportFile(cleanOnly: boolean) {
  busy.value = true;
  try {
    exportResult.value = await exportMutation.mutateAsync({ id: taskId.value, cleanOnly });
    message.success("文件已生成");
    await queryClient.invalidateQueries({ queryKey: ["reports"] });
  } catch (error: any) {
    message.error(error.message);
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <div class="mb-8 flex items-center justify-between">
    <div>
      <div class="text-sm font-semibold uppercase tracking-widest text-[#b44236]">任务执行</div>
      <h1 class="mt-2 text-3xl font-bold text-slate-800">房源数据清洗</h1>
      <p class="mt-2 text-slate-500">从原始文件到标准导入文件，逐步确认每一个关键结果。</p>
    </div>
    <n-tag v-if="taskId" type="info" round>任务 {{ taskId }}</n-tag>
  </div>

  <n-spin :show="busy">
    <n-card v-if="step === 1" title="创建清洗批次" class="shadow-sm">
      <p class="mb-5 text-slate-500">请选择本次数据对应的业务类型。</p>
      <n-space>
        <n-button :type="kind === 'sale' ? 'primary' : 'default'" size="large" @click="kind = 'sale'">出售房源</n-button>
        <n-button :type="kind === 'rent' ? 'primary' : 'default'" size="large" @click="kind = 'rent'">出租房源</n-button>
      </n-space>
      <div class="mt-6"><n-button type="primary" :disabled="!kind" @click="createTask">创建任务并上传文件</n-button></div>
    </n-card>

    <n-card v-else-if="step === 2" title="上传原始文件" class="shadow-sm">
      <input type="file" accept=".csv,.xls,.xlsx" class="mb-5 block w-full rounded border border-dashed border-slate-300 bg-white p-8" @change="handleFileChange" />
      <n-alert v-if="sheets.length" type="success" title="文件识别完成" class="mb-4">请选择要清洗的工作表。</n-alert>
      <div v-for="sheet in sheets" :key="sheet.name" class="mb-3 flex items-center justify-between rounded-lg border bg-white p-4">
        <div>
          <div class="font-medium">{{ sheet.name }}</div>
          <div class="text-sm text-slate-500">{{ sheet.rows }} 条记录 · {{ sheet.cols }} 列 · 表头第 {{ sheet.headerRow }} 行</div>
        </div>
        <n-button type="primary" secondary @click="selectSheet(sheet)">选择工作表</n-button>
      </div>
    </n-card>

    <n-card v-else-if="step === 3" title="确认字段映射" class="shadow-sm">
      <div class="overflow-x-auto">
        <table class="w-full text-left text-sm">
          <thead><tr class="border-b text-slate-500"><th class="p-3">原始字段</th><th class="p-3">目标字段</th><th class="p-3">置信度</th><th class="p-3">判断依据</th></tr></thead>
          <tbody>
            <tr v-for="item in suggestions" :key="item.source" class="border-b">
              <td class="p-3 font-medium">{{ item.source }}</td>
              <td class="p-3"><n-select v-model:value="mapping[item.source]" :options="[{ label: '不导入', value: '__ignore__' }, ...targets.map((target) => ({ label: target, value: target }))]" /></td>
              <td class="p-3">{{ Math.round(item.confidence * 100) }}%</td>
              <td class="p-3 text-slate-500">{{ item.reason }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <n-button class="mt-6" type="primary" @click="confirmMapping">确认映射，检查楼盘</n-button>
    </n-card>

    <n-card v-else-if="step === 4" title="楼盘审核" class="shadow-sm">
      <n-alert class="mb-4">自动匹配结果会直接应用；以下项目需要人工选择。</n-alert>
      <div v-for="(review, index) in estateReviews" :key="review.key || index" class="mb-4 rounded-lg border p-4">
        <div class="mb-3 font-medium">{{ review.raw || "空值" }} <span class="text-sm text-slate-400">影响 {{ review.rows.length }} 行</span></div>
        <n-radio-group v-model:value="estateSelected[review.key || review.raw]">
          <n-space vertical>
            <n-radio v-for="candidate in review.candidates" :key="candidate.match_name || candidate.楼盘" :value="candidate.match_name || candidate.楼盘">
              {{ candidate.match_name || candidate.楼盘 }} · {{ candidate.行政区 }} · {{ candidate.商圈 }}
            </n-radio>
            <n-radio value="">暂不匹配</n-radio>
          </n-space>
        </n-radio-group>
      </div>
      <n-button type="primary" @click="confirmEstate">保存确认并检查栋座</n-button>
    </n-card>

    <n-card v-else-if="step === 5" title="栋座审核" class="shadow-sm">
      <n-alert class="mb-4">只有无法唯一确认的栋座需要选择。</n-alert>
      <div v-for="(review, index) in buildingReviews" :key="review.key || index" class="mb-4 rounded-lg border p-4">
        <div class="mb-3 font-medium">{{ review.estate }} · {{ review.raw }}</div>
        <n-radio-group v-model:value="buildingSelected[review.key]">
          <n-space vertical>
            <n-radio v-for="candidate in review.candidates" :key="candidate" :value="candidate">{{ candidate }}</n-radio>
            <n-radio value="">暂不匹配</n-radio>
          </n-space>
        </n-radio-group>
      </div>
      <div class="mb-5 max-w-xs">
        <div class="mb-2 text-sm text-slate-500">统一委托日期</div>
        <n-date-picker v-model:value="entrustDate" type="date" />
      </div>
      <n-button type="primary" @click="confirmBuilding">保存确认并进入导出</n-button>
    </n-card>

    <n-card v-else title="导出结果" class="shadow-sm">
      <n-result v-if="!exportResult" status="info" title="清洗已完成" description="请选择导出方式" />
      <div v-else class="mb-5 rounded-lg bg-emerald-50 p-4 text-emerald-800">
        已生成 {{ exportResult.report?.最终输出记录数 }} 条记录，阻断异常 {{ exportResult.report?.阻断异常数量 }} 条。
      </div>
      <n-space>
        <n-button type="primary" @click="exportFile(false)">导出全部数据</n-button>
        <n-button secondary @click="exportFile(true)">仅导出无阻断异常</n-button>
        <n-button v-if="exportResult?.downloadId" tag="a" :href="`/download/${exportResult.downloadId}`" target="_blank" tertiary>下载文件</n-button>
      </n-space>
      <div class="mt-6"><n-button text @click="resetTask">开始新任务</n-button></div>
    </n-card>
  </n-spin>
</template>
