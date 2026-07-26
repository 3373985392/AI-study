---
layout: page
title: 标签
---

<script setup>
import { data as posts } from './posts.data.ts'

const tagMap = {}
for (const post of posts) {
  for (const tag of post.tags) {
    if (!tagMap[tag]) tagMap[tag] = []
    tagMap[tag].push(post)
  }
}
const tags = Object.keys(tagMap).sort()
</script>

<div class="tags-page">
  <div v-for="tag in tags" :key="tag" class="tag-section">
    <h2 :id="tag"><a :href="`#${tag}`"># {{ tag }}</a></h2>
    <ul>
      <li v-for="post in tagMap[tag]" :key="post.url">
        <a :href="post.url">{{ post.title }}</a>
        <span class="date">{{ post.formattedDate }}</span>
      </li>
    </ul>
  </div>
</div>
