<script setup lang="ts">
import { computed, h, ref } from "vue";
import { useQuery } from "@tanstack/vue-query";
import {
  NButton,
  NCard,
  NDataTable,
  NEmpty,
  NInput,
  NModal,
  NPagination,
  NSelect,
  NSpace,
  NSpin,
  NTag,
  NCode,
  useMessage,
} from "naive-ui";
import { api, type BatchKind, type ReportItem } from "../../api";

const message = useMessage();
const search = ref("");
const reportPage = ref(1);
const reportPageSize = ref(10);
const reportKind = ref<BatchKind | undefined>();
const showRules = ref(false);
const selectedReport = ref<ReportItem | null>(null);

const reportQuery = useQuery({
  queryKey: computed(() => ["reports", reportPage.value, reportPageSize.value, reportKind.value]),
  queryFn: () => api.reports(reportPage.value, reportPageSize.value, reportKind.value),
});

const filteredReports = computed(() => {
  const items = reportQuery.data.value?.items ?? [];
  const keyword = search.value.trim().toLowerCase();
  if (!keyword) return items;
  return items.filter((item: ReportItem) =>
    item.original_name.toLowerCase().includes(keyword) || item.task_id.toLowerCase().includes(keyword),
  );
});

function downloadUrl(row: ReportItem) {
  if (row.output_url) return row.output_url;
  return row.output_file ? `/download/${row.output_file.split(/[\\/]/).map(encodeURIComponent).join("/")}` : "";
}

function openReport(row: ReportItem) {
  if (row.output_file) window.open(downloadUrl(row), "_blank");
  else message.info("该报告没有可下载的文件");
}

function openRules(row: ReportItem) {
  selectedReport.value = row;
  showRules.value = true;
}

function formatRules(row: ReportItem | null) {
  return JSON.stringify(row?.report?.["清洗规则"] ?? {}, null, 2);
}

function updatePageSize(value: number) {
  reportPageSize.value = value;
  reportPage.value = 1;
}

function updateReportKind(value: BatchKind | null) {
  reportKind.value = value ?? undefined;
  reportPage.value = 1;
}

const reportColumns = [
  {
    title: "任务",
    key: "task_id",
    render: (row: ReportItem) => h("div", [
      h("div", { class: "font-medium" }, row.task_id),
      h("div", { class: "text-xs text-slate-400" }, row.original_name),
    ]),
  },
  {
    title: "类型",
    key: "kind",
    render: (row: ReportItem) => h(
      NTag,
      { type: row.kind === "sale" ? "error" : "info", bordered: false },
      { default: () => (row.kind === "sale" ? "出售" : "出租") },
    ),
  },
  { title: "记录", key: "output_rows", render: (row: ReportItem) => `${row.output_rows} / ${row.input_rows}` },
  {
    title: "阻断异常",
    key: "blocking_count",
    render: (row: ReportItem) => h(
      NTag,
      { type: row.blocking_count ? "warning" : "success", bordered: false },
      { default: () => String(row.blocking_count) },
    ),
  },
  { title: "完成时间", key: "completed_at" },
  {
    title: "操作",
    key: "actions",
    render: (row: ReportItem) => h(NSpace, { size: 8 }, {
      default: () => [
        h(NButton, { size: "small", tertiary: true, onClick: () => openRules(row) }, { default: () => "查看规则" }),
        h(NButton, { size: "small", tertiary: true, onClick: () => openReport(row) }, { default: () => "下载文件" }),
      ],
    }),
  },
];
</script>

<template>
  <div class="mb-8">
    <div>
      <div class="text-sm font-semibold uppercase tracking-widest text-tsinghua">历史报告</div>
      <h1 class="mt-2 text-3xl font-bold text-slate-800">清洗任务记录</h1>
      <p class="mt-2 text-slate-500">所有已完成的导出任务都会在这里留下报告。</p>
    </div>
    <div class="mt-6 flex flex-nowrap items-center gap-3 overflow-x-auto">
      <n-input v-model:value="search" class="!w-72 shrink-0" clearable placeholder="搜索任务或文件名" />
      <n-select
        :value="reportKind"
        clearable
        class="!w-28 shrink-0"
        placeholder="全部类型"
        :options="[{ label: '出售', value: 'sale' }, { label: '出租', value: 'rent' }]"
        @update:value="updateReportKind"
      />
    </div>
  </div>

  <n-card class="shadow-sm">
    <n-spin :show="reportQuery.isLoading.value">
      <n-data-table :columns="reportColumns" :data="filteredReports" :bordered="false" :single-line="false" />
      <n-empty v-if="!reportQuery.isLoading.value && !filteredReports.length" description="暂无历史报告" class="py-16" />
      <div class="mt-5 flex flex-wrap items-center justify-end gap-3">
        <span class="text-sm text-slate-500">每页</span>
        <n-select
          :value="reportPageSize"
          class="!w-20 shrink-0"
          :options="[10, 20, 30, 50].map((value) => ({ label: `${value}条/页`, value }))"
          @update:value="updatePageSize"
        />
        <n-pagination v-model:page="reportPage" :page-size="reportPageSize" :item-count="reportQuery.data.value?.total ?? 0" />
      </div>
    </n-spin>
  </n-card>

  <n-modal v-model:show="showRules" preset="card" title="清洗规则快照" style="width: min(960px, calc(100vw - 32px));">
    <template v-if="selectedReport?.report?.['清洗规则']">
      <p class="mb-4 text-sm text-slate-500">
        以下内容是该任务导出时实际使用的规则快照，不会随当前规则变化而改变。
      </p>
      <n-code :code="formatRules(selectedReport)" language="json" word-wrap />
    </template>
    <n-empty v-else description="该历史报告没有保存清洗规则快照" class="py-12" />
  </n-modal>
</template>
