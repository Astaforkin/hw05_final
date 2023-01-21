from django.contrib.auth import get_user_model
from django.test import TestCase

from ..models import Group, Post, Comment, Follow, LEN_TEXT

User = get_user_model()


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='test_user')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            group=cls.group,
            text='Тестовый пост тестового пользователя в тестовой группе',
        )

    def test_models_have_correct_object_names(self):
        """Проверяем, что у моделей корректно работает __str__."""
        post = PostModelTest.post
        group = PostModelTest.group
        self.assertEqual(post.text[:LEN_TEXT], str(post))
        self.assertEqual(group.title, str(group))

    def test_models_have_verbose_name(self):
        """verbose_name в полях совпадает с ожидаемым."""
        post = PostModelTest.post
        field_verboses = {
            'text': 'Текст поста',
            'group': 'Группа'
        }
        for field, expected_value in field_verboses.items():
            with self.subTest(field=field):
                self.assertEqual(
                    post._meta.get_field(field).verbose_name, expected_value)

    def test_models_have_help_text(self):
        """help_text в полях совпадает с ожидаемым."""
        post = PostModelTest.post
        field_help_texts = {
            'text': 'Введите текст поста',
            'group': 'Группа, к которой будет относиться пост',
        }
        for field, expected_value in field_help_texts.items():
            with self.subTest(field=field):
                self.assertEqual(
                    post._meta.get_field(field).help_text, expected_value)


class CommentModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username="test_user")

    def setUp(self):
        self.post = Post.objects.create(
            author=self.user,
            text="Тестовый пост тестового пользователя в тестовой группе",
        )
        self.add_comment = Comment.objects.create(
            author=self.user,
            post=self.post,
            text='Тестовый пост тестового пользователя в тестовом комментарии'
        )

    def test_verbose_name_post(self):
        """help_text для Comment в полях совпадает с ожидаемым."""
        field_verboses = {
            "author": "Автор",
            "post": "Пост",
            "text": "Текст комментария",
        }
        for field, expected_value in field_verboses.items():
            with self.subTest(field=field):
                self.assertEqual(
                    self.add_comment._meta.get_field(
                        field).verbose_name, expected_value
                )

    def test_comment_and_delete(self):
        '''Проверка нового поста и удаление'''
        post = Post.objects.create(
            author=CommentModelTest.user,
            text="Тестовый пост тестового пользователя в тестовом комментари2",
        )
        self.assertEqual(self.add_comment.author,
                         CommentModelTest.user)
        self.assertEqual(self.add_comment.post,
                         self.post)
        self.assertEqual(Comment.objects.filter(post=post).count(), 0)
        self.assertEqual(Comment.objects.filter(post=self.post).count(), 1)
        self.add_comment.delete()
        self.assertEqual(Comment.objects.count(), 0)


class FollowModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_one = User.objects.create_user(username="test_user")
        cls.user_two = User.objects.create_user(username="other_test_user")

    def setUp(self):
        self.follow = Follow.objects.create(user=self.user_one,
                                            author=self.user_two)

    def test_verbose_name_post(self):
        """help_text для Follow в полях совпадает с ожидаемым."""
        field_verboses = {
            "author": "Автор",
            "user": "Подписчик",
        }
        for field, expected_value in field_verboses.items():
            with self.subTest(field=field):
                self.assertEqual(
                    self.follow._meta.get_field(
                        field).verbose_name, expected_value
                )

    def test_add_new_following(self):
        '''Проверка на добавление нового подписчика'''
        self.assertEqual(self.follow.user,
                         FollowModelTest.user_one)
        self.assertEqual(self.follow.author,
                         FollowModelTest.user_two)

    def test_unfollowing(self):
        '''Проверка отписки'''
        self.follow.delete()
        self.assertEqual(Follow.objects.count(), 0)
