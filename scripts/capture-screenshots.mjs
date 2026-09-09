import { mkdir } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import path from 'node:path'
import playwright from '../frontend/node_modules/playwright-core/index.js'

const { chromium } = playwright

const knowledgeBaseId = process.argv[2]
if (!knowledgeBaseId) {
  throw new Error('Usage: node scripts/capture-screenshots.mjs <knowledge-base-id>')
}

const repositoryRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const outputDirectory = path.join(repositoryRoot, 'docs', 'screenshots')
const baseUrl = process.env.DOCPILOT_WEB_BASE ?? 'http://127.0.0.1:3000'

await mkdir(outputDirectory, { recursive: true })

const browser = await chromium.launch({ channel: 'msedge', headless: true })
const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 })
page.setDefaultTimeout(30_000)

async function capture(name) {
  await page.screenshot({ path: path.join(outputDirectory, name), fullPage: true })
  console.log(`captured ${name}`)
}

try {
  const knowledgeBaseUrl = `${baseUrl}/knowledge-bases/${knowledgeBaseId}`

  await page.goto(knowledgeBaseUrl, { waitUntil: 'networkidle' })
  await page.getByText('处理完成').first().waitFor()
  await capture('knowledge-base.png')

  await page.goto(`${knowledgeBaseUrl}/chat`, { waitUntil: 'networkidle' })
  await page.getByLabel('问题').fill('退款申请需要在签收后多少天内提交？')
  await page.getByLabel('问题').press('Enter')
  await page.getByText('依据资料回答').waitFor()
  await capture('chat-citations.png')

  await page.getByLabel('问题').fill('火星基地明天的午餐菜单是什么？')
  await page.getByLabel('问题').press('Enter')
  await page.getByText('资料不足').waitFor()
  await capture('refusal.png')

  await page.goto(`${knowledgeBaseUrl}/debug`, { waitUntil: 'networkidle' })
  await page.getByLabel('调试问题').fill('专业版提供多少团队存储空间？')
  await page.getByRole('button', { name: '运行检索' }).click()
  await page.getByRole('heading', { name: '候选结果' }).waitFor()
  await capture('retrieval-debug.png')

  await page.goto(`${knowledgeBaseUrl}/evaluations`, { waitUntil: 'networkidle' })
  await page.getByRole('button', { name: '运行全部评测' }).click()
  await page.getByText('100%', { exact: true }).waitFor()
  await capture('evaluation.png')
} finally {
  await browser.close()
}
