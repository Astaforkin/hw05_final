from django import forms
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse

from ..models import Group, Post, User, Follow
from ..paginators import LAST_POSTS

User = get_user_model()


class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='test_user')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Тестовое описание группы',
        )
        cls.post = Post.objects.create(
            text='Тестовый текст поста',
            author=cls.user,
            group=cls.group,
        )

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.user_follower = User.objects.create_user(username='follower')
        self.authorized_client_fol = Client()
        self.authorized_client_fol.force_login(self.user_follower)
        self.user_not_follower = User.objects.create_user(
            username='notfollower'
        )
        self.authorized_client_not_fol = Client()
        self.authorized_client_not_fol.force_login(self.user_follower)
        cache.clear()

    def check_post_info(self, post):
        with self.subTest(post=post):
            self.assertEqual(post.text, self.post.text)
            self.assertEqual(post.author, self.post.author)
            self.assertEqual(post.group.id, self.post.group.id)
            self.assertEqual(post.image, self.post.image)

    def test_forms_show_correct(self):
        """Проверка коректности формы."""
        context = {
            reverse('posts:post_create'),
            reverse('posts:post_edit', kwargs={'post_id': self.post.id, }),
        }
        for reverse_page in context:
            with self.subTest(reverse_page=reverse_page):
                response = self.authorized_client.get(reverse_page)
                self.assertIsInstance(
                    response.context['form'].fields['text'],
                    forms.fields.CharField)
                self.assertIsInstance(
                    response.context['form'].fields['group'],
                    forms.fields.ChoiceField)

    def test_index_page_show_correct_context(self):
        """Шаблон index.html сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:index'))
        self.check_post_info(response.context['page_obj'][0])

    def test_groups_page_show_correct_context(self):
        """Шаблон group_list.html сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse(
                'posts:group_list',
                kwargs={'slug': self.group.slug})
        )
        self.assertEqual(response.context['group'], self.group)
        self.check_post_info(response.context['page_obj'][0])

    def test_profile_page_show_correct_context(self):
        """Шаблон profile.html сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse(
                'posts:profile',
                kwargs={'username': self.user.username}))
        self.assertEqual(response.context['author'], self.user)
        self.check_post_info(response.context['page_obj'][0])

    def test_detail_page_show_correct_context(self):
        """Шаблон post_detail.html сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse(
                'posts:post_detail',
                kwargs={'post_id': self.post.id}))
        self.check_post_info(response.context['post'])

    def test_index_page_cache_correct(self):
        """Кеш главной страницы работает правильно."""
        response = self.authorized_client.get(reverse('posts:index'))
        temp_post = Post.objects.get(id=1)
        temp_post.delete()
        new_response = self.authorized_client.get(reverse('posts:index'))
        self.assertEqual(response.content, new_response.content)
        cache.clear()
        new_new_response = self.authorized_client.get(reverse('posts:index'))
        self.assertNotEqual(response.content, new_new_response.content)

    def test_authorized_user_can_follow_unfollow(self):
        """
        Авторизованный пользователь может подписываться на других
        пользователей и отписываться от них
        """
        author = self.user
        user = self.user_follower
        self.authorized_client_fol.get(
            reverse('posts:profile_follow',
                    kwargs={'username': author.username})
        )
        self.assertTrue(Follow.objects.filter(user=user,
                                              author=author).exists())
        self.authorized_client_fol.get(
            reverse('posts:profile_unfollow',
                    kwargs={'username': author.username})
        )
        self.assertFalse(Follow.objects.filter(user=user,
                                               author=author).exists())

    def test_post_appears_in_feed(self):
        """
        Новая запись пользователя появляется в ленте тех, кто на него
        подписан и не появляется в ленте тех, кто не подписан.
        """
        author = self.user
        user_follow = self.user_follower
        user_not_follow = self.user_not_follower
        self.authorized_client_fol.get(
            reverse('posts:profile_follow',
                    kwargs={'username': author.username})
        )
        authors = Follow.objects.values_list('author').filter(user=user_follow)
        post_list = Post.objects.filter(author__in=authors)
        new_post = Post.objects.create(author=author,
                                       text='Тестовый текст',)
        self.assertIn(new_post, post_list)
        new_authors = Follow.objects.values_list('author').filter(
            user=user_not_follow
        )
        new_post_list = Post.objects.filter(author__in=new_authors)
        self.assertNotIn(new_post, new_post_list)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(
            username='test_user',
        )
        cls.group = Group.objects.create(
            title='Тестовое название группы',
            slug='test_slug',
            description='Тестовое описание группы',
        )
        number_of_posts = 13
        posts = [Post(text=f'Тестовый текст {i}',
                      group=cls.group,
                      author=cls.user)
                 for i in range(number_of_posts)]
        Post.objects.bulk_create(posts)
        cls.posts_on_second_page = number_of_posts - LAST_POSTS
        cls.pages = (
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': cls.group.slug}),
            reverse('posts:profile', kwargs={'username': cls.user.username}),
        )

    def setUp(self):
        self.user_not_authorized = Client()
        cache.clear()

    def test_paginator_on_pages(self):
        """Проверка пагинации на страницах."""
        for reverse_ in self.pages:
            with self.subTest(reverse_=reverse_):
                self.assertEqual(len(self.user_not_authorized.get(
                    reverse_).context.get('page_obj')),
                    LAST_POSTS
                )
                self.assertEqual(len(self.user_not_authorized.get(
                    reverse_ + '?page=2').context.get('page_obj')),
                    self.posts_on_second_page
                )
