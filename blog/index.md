---
layout: page
title: 博客
---

<script setup>
import { data as posts } from './posts.data.ts'
import { withBase } from 'vitepress'
</script>

<div class="blog-list">
  <article v-for="post in posts" :key="post.url" class="post-card">
    <header>
      <h2 class="post-title">
        <a :href="withBase(post.url)">{{ post.title }}</a>
      </h2>
      <div class="post-meta">
        <time :datetime="post.date">{{ post.formattedDate }}</time>
        <span>{{ post.readingTime }} 分钟阅读</span>
      </div>
    </header>
    <div v-if="post.tags.length">
      <span v-for="tag in post.tags" :key="tag" class="tag">
        <a :href="withBase(`/blog/tags#${tag}`)">{{ tag }}</a>
      </span>
    </div>
    <p class="post-excerpt" v-if="post.excerpt">{{ post.excerpt }}</p>
  </article>

  <div v-if="posts.length === 0" class="empty">
    还没有文章，开始写第一篇吧！
  </div>
</div>
